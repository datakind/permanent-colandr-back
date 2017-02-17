package org.datakind.ci.pdfestrian.extraction

import cc.factorie.app.classify.LinearVectorClassifier
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la.{DenseTensor1, SparseTensor1, Tensor1}
import cc.factorie.optimize.{AdaGradRDA, OnlineTrainer, PredictorExample}
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.api.{Metadata, Record}
import org.datakind.ci.pdfestrian.scripts.AidSeq
import org.json4s.DefaultFormats
import spray.caching.LruCache
import spray.util._

import scala.concurrent.ExecutionContext.Implicits.global
import scala.io.Source
import scala.util.Random

sealed trait ValueType
object Multi extends ValueType
object Single extends ValueType

case class ReviewLabel(labelName : String, allowedValues : Set[String], value : ValueType, trainingSize : Int)
class ReviewModel(val labels : Map[String, ReviewLabel],
                  labelCounts : Map[String, Int],
                  numTrainDocuments : Int,
                  featureExtractor : CombinedSent
                 ) {

  lazy val weight = labelDomain.map { bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = labelCounts(name)
    val tw = (numTrainDocuments - count).toDouble / count.toDouble
    intval -> tw
  }.sortBy(_._1).map {
    _._2
  }.toArray

  lazy val dWeight = new DenseTensor1(weight)

  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map {
    _.toLowerCase
  }.toSet

  object labelDomain extends CategoricalDomain[String]

  class RankLabel(label: String, val feature: RankFeatures, val labels: Seq[String], val doc: Document, val sentence: Sentence) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = labelDomain

    def multiLabel: DenseTensor1 = {
      val dt = new DenseTensor1(labelDomain.size)
      for (l <- labels) {
        dt(labelDomain.index(l)) = 1.0
      }
      dt
    }
  }

  object featuresDomain extends VectorDomain {
    override type Value = SparseTensor1

    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(featureExtractor.featureSize)
  }

  class RankFeatures(st1: SparseTensor1) extends VectorVariable(st1) {
    def domain = featuresDomain
  }

  def clean(string: String): String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(pl: Document, labels: Seq[String]): Seq[RankLabel] = {
    if(labels.isEmpty)
      return Seq()
    val sentences = pl.sentences.toArray
      .filterNot(s => s.string.contains("org.apache"))
      .filter(_.string.length > 70)
    val length = sentences.length
    sentences.zipWithIndex.map { case (sent, i) =>
      val f = featureExtractor(sent, i.toDouble / length.toDouble, pl.name)
      val features = new RankFeatures(f)
      for (l <- labels) {
        new RankLabel(l, features, labels, pl, sent)
      }
      new RankLabel(labels.headOption.getOrElse(labelDomain.categories.head), features, labels, pl, sent)
    }
  }

  def sigmoid(d: Double): Double = {
    1.0 / (1.0f + math.exp(-d))
  }

  def l2f(l: RankLabel) = l.feature

  var classifier : Option[Classifier] = None

  def train(trainingData: Seq[TrainingData]) : Classifier = {
    classifier = Some(new Classifier(train(trainingData.flatMap(trainDataToFeature), 0.000005)))
    classifier.get
  }

  def train(trainData: Seq[RankLabel], l2: Double) : LinearVectorClassifier[RankLabel, RankFeatures] = {
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(labelDomain.size, featuresDomain.dimensionSize, (l: RankLabel) => l.feature)
    val trainer = new OnlineTrainer(classifier.parameters, optimizer = rda, maxIterations = 5)

    val trainExamples = trainData.map { td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new LossFunctions.WeightedSigmoidalLoss(dWeight))
    }

    while (!trainer.isConverged) {
      val shuffed = Random.shuffle(trainExamples)
      trainer.processExamples(shuffed)
    }

    classifier
  }

  def trainDataToFeature(td : TrainingData) : Seq[RankLabel] = {
    val labels = td.labels.flatMap{
      case MultiValue(labelName, values) => values.map{ v => labelName + ":" + v }
      case SingleValue(labelName, value) => Array(labelName + ":" + value)
    }
    docToFeature(PDFToDocument.fromString(td.fullText, td.id.toString)._1, labels)
  }

  def createClassifier(): Classifier = {
    val model = new LinearVectorClassifier[RankLabel, RankFeatures](labelDomain.dimensionSize, featuresDomain.dimensionSize, (l: RankLabel) => l.feature)
    new Classifier(model)
  }

  class Classifier(val classifier: LinearVectorClassifier[RankLabel, RankFeatures]) {
    type label = RankLabel
    type feature = RankFeatures
    val domain = labelDomain
    val fDomain = featuresDomain

    def classify(l: label) = {
      classifier.classification(l.feature.value).prediction
    }

    def classify(l: Tensor1) = {
      classifier.classification(l).prediction
    }

    def classify(d: Document, threshold : Double = 0.5): Seq[(String, String, Int, Double)] = {
      val labels = docToFeature(d, Seq(labelDomain.categories.head))
      labels.flatMap { l =>
        classifier.classification(l.feature.value).prediction.toArray
          .zipWithIndex.map { p => (p._2, p._1, l.sentence) }
          .filter(l => sigmoid(l._2) > threshold).map { p =>
          val document = l.sentence.document
          val sentences = (math.max(0,l.sentence.indexInSection-3) until math.min(document.sentenceCount-1, l.sentence.indexInSection+3)).map{ i =>
            document.asSection.sentences(i).tokensString(" ")
          }.mkString("\n")
          (domain(p._1).category, sentences, l.sentence.indexInSection, sigmoid(p._2))
        }
      }.groupBy(_._1).flatMap {
        _._2.sortBy(-_._4).take(3)
      }.toSeq
    }

    def classifySentences(d: Document) = {
      val classification = classify(d)
      classification.groupBy(_._3).map { s =>
        val classes = s._2.map { klass =>
          (klass._1, klass._4)
        }
        SentenceClassifications(s._1, s._2.head._2, classes)
      }.toArray.sortBy(_.index)
    }

    def getMetaData(record : Record, threshold : Double) : Seq[Metadata] = {
      val (d, _) = PDFToDocument.fromString(record.content, record.filename)
      classify(d, threshold).map { r =>
        val split = r._1.split(":",2)
        val (labelName, value) = (split.head, split.last)
        Metadata(record.id.toString, labelName, value, r._2, r._3, r._4)
      }
    }

    def getSentences(record: Record) : Seq[SentenceClassifications] = {
      val (d, _) = PDFToDocument.fromString(record.content, record.filename)
      classifySentences(d)
    }

  }

}

class ReviewModelTrainer(minLabels : Int, increaseRequirement : Int) {


  def splitLabels(trainingData: Array[TrainingData]) = {
    trainingData.flatMap(_.labels).foldRight(Map[String, ReviewLabel]()){ case (label, map) =>
      label match {
        case MultiValue(labelName, values) =>
          val l = map.getOrElse(labelName, ReviewLabel(labelName, Set(), Multi, 0))
          val updated = l.copy(allowedValues = l.allowedValues ++ values.toSet, trainingSize = l.trainingSize + values.length)
          map + (labelName -> updated)
        case SingleValue(labelName, value) =>
          val l = map.getOrElse(labelName, ReviewLabel(labelName, Set(), Single, 0))
          val updated = l.copy(allowedValues = l.allowedValues + value, trainingSize = l.trainingSize + 1)
          map + (labelName -> updated)
      }
    }
  }

  def compareAndTrain(prevModel : ReviewModel, trainingData: Array[TrainingData], reviewId : Int) : (Boolean, ReviewModel) = {
    splitLabels(trainingData).filter(_._2.trainingSize > minLabels) match {
      case a : Map[String, ReviewLabel] if a.map(_._2.trainingSize).sum > prevModel.labels.map(_._2.trainingSize).sum + increaseRequirement =>
        (true, train(reviewId))
      case a : Map[String, ReviewLabel] =>
        (false, prevModel)
    }
  }

  def startTrain(trainingData : Array[TrainingData], reviewId : Int) : Option[ReviewModel] = {
    val labels = splitLabels(trainingData)
    labels.filter(_._2.trainingSize > minLabels) match {
      case a : Map[String, ReviewLabel] if a.isEmpty => None
      case a : Map[String, ReviewLabel] => Some(train(reviewId))
    }
  }

  def train(reviewId : Int) : ReviewModel = {

    val trainingData = GetTrainingData(reviewId)
    val labels = splitLabels(trainingData)

    val labelCounts = trainingData.flatMap(_.labels)
                                    .flatMap{
                                      case MultiValue(labelName, values) => values.map(v => labelName + ":" + v)
                                      case SingleValue(labelName, value) => Array(labelName + ":" + value)
                                    }
                                  .foldRight(Map[String, Int]()) { case (label, map) =>
      map + (label -> (map.getOrElse(label, 0) + 1))
    }

    val featureExtractor = CombinedSent(trainingData)

    val model = new ReviewModel(labels, labelCounts, trainingData.length, featureExtractor)
    model.train(trainingData)
    model
  }
}
object ReviewTrainer {

  import org.json4s.jackson.Serialization.write
  implicit val formats = DefaultFormats

  val cache = LruCache.apply[ReviewModel](maxCapacity = 25, initialCapacity = 10)

  def getModel(review : Int, minRequired : Int = 40, increaseRequirement : Int = 5) : Option[ReviewModel] = {
    val trainer = new ReviewModelTrainer(minRequired, increaseRequirement)
    cache.get(review) match {
      case None =>
        trainer.startTrain(GetTrainingData.labelsOnly(review), review) match {
          case None => None
          case Some(model) =>
            cache(review)(model)
            Some(model)
        }
      case Some(modelFuture) =>
        modelFuture.map{ model =>
          trainer.compareAndTrain(model, GetTrainingData.labelsOnly(review), review) match {
            case (true, newModel) =>
              cache.remove(review)
              cache(review)(newModel)
              Some(newModel)
            case (false, oldModel) =>
              Some(oldModel)
          }
        }.await
    }
  }


  def main(args: Array[String]): Unit = {
    val data = GetTrainingData(1).head
    println(data.id)
    val exRecord = Record(data.id, 1, data.id, data.id.toString, data.fullText)
    val model = getModel(1)
    println(write(model.get.classifier.get.getMetaData(exRecord, 0.75)))
    val model2 = getModel(1)
    println(write(model2.get.classifier.get.getMetaData(exRecord, 0.75)))
  }

}
