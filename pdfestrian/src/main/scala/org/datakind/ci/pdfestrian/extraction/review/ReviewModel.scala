package org.datakind.ci.pdfestrian.extraction.review

import cc.factorie.app.classify.LinearVectorClassifier
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la.{DenseTensor1, SparseTensor1, Tensor1}
import cc.factorie.optimize.{AdaGradRDA, OnlineTrainer, PredictorExample}
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.api.apiservice.{Metadata, Record}
import org.datakind.ci.pdfestrian.document.PDFToDocument
import org.datakind.ci.pdfestrian.extraction.features.CombinedSent
import org.datakind.ci.pdfestrian.lossfunctions.LossFunctions
import org.datakind.ci.pdfestrian.trainingData.{MultiValue, SingleValue, TrainingData}

import scala.util.Random

/**
  * Review model has the ability to train with training data, and build a classifier
  * @param labels list of labels, labelname -> [[ReviewLabel]]
  * @param labelCounts Count of labels labelname -> counts
  * @param numTrainDocuments number of documents in training set
  * @param featureExtractor feature extractor which take doc => feature vector
  * @param pdf2Doc converts fulltxt to PDF
  */
class ReviewModel(val labels : Map[String, ReviewLabel],
                  labelCounts : Map[String, Int],
                  numTrainDocuments : Int,
                  featureExtractor : CombinedSent,
                  pdf2Doc : PDFToDocument
                 ) {

  private lazy val weight = labelDomain.map { label =>
    val name = label.category
    val intval = label.intValue
    val count = labelCounts(name)
    val tw = (numTrainDocuments - count).toDouble / count.toDouble
    intval -> tw
  }.sortBy(_._1).map {
    _._2
  }.toArray

  private lazy val dWeight = new DenseTensor1(weight)

  private implicit val rand = new Random()

  protected object labelDomain extends CategoricalDomain[String]

  protected class RankLabel(label: String, val feature: RankFeatures, val labels: Seq[String], val doc: Document, val sentence: Sentence) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = labelDomain

    def multiLabel: DenseTensor1 = {
      val dt = new DenseTensor1(labelDomain.size)
      for (l <- labels) {
        dt(labelDomain.index(l)) = 1.0
      }
      dt
    }
  }

  protected object featuresDomain extends VectorDomain {
    override type Value = SparseTensor1

    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(featureExtractor.featureSize)
  }

  protected class RankFeatures(st1: SparseTensor1) extends VectorVariable(st1) {
    def domain = featuresDomain
  }

  private def clean(string: String): String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  private def docToFeature(pl: Document, labels: Seq[String]): Seq[RankLabel] = {
    if(labels.isEmpty)
      return Seq()
    val sentences = pl.sentences.toArray
      .filterNot(s => s.string.contains("org.apache") || s.string.contains("WARN") || s.string.contains("DEBUG"))
      .filter(_.string.length > 50)
    val length = sentences.length
    sentences.zipWithIndex.map { case (sent, i) =>
      val f = featureExtractor(sent, i.toDouble / length.toDouble)
      val features = new RankFeatures(f)
      for (l <- labels) {
        new RankLabel(l, features, labels, pl, sent)
      }
      new RankLabel(labels.headOption.getOrElse(labelDomain.categories.head), features, labels, pl, sent)
    }
  }

  private def sigmoid(d: Double): Double = {
    1.0 / (1.0f + math.exp(-d))
  }

  private def l2f(l: RankLabel) = l.feature

  var classifier : Option[Classifier] = None

  /**
    * Trains a classifier and sets [[classifier]] to the trained classifier
    * @param trainingData training data to train the classifier
    * @return Returns the [[Classifier]] stored in [[classifier]] trained using trainingData
    */
  def train(trainingData: Seq[TrainingData]) : Classifier = {
    classifier = Some(new Classifier(train(trainingData.flatMap(trainDataToFeature), 0.000005)))
    classifier.get
  }

  private def train(trainData: Seq[RankLabel], l1: Double) : LinearVectorClassifier[RankLabel, RankFeatures] = {
    val rda = new AdaGradRDA(l1 = l1)
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

  private def trainDataToFeature(td : TrainingData) : Seq[RankLabel] = {
    val featurelabels = td.labels.flatMap{
      case MultiValue(labelName, values) => values.map{ v => labelName + ":" + v }
      case SingleValue(labelName, value) => Array(labelName + ":" + value)
    }.filter { label =>
      val split = label.split(':').head
      labels.contains(split)
    }
    docToFeature(pdf2Doc.fromString(td.fullText, td.id.toString)._1, featurelabels)
  }

  /** Classifier takes in a LVC and can get classify documents and vectores **/
  class Classifier(val classifier: LinearVectorClassifier[RankLabel, RankFeatures]) {
    type label = RankLabel
    type feature = RankFeatures
    val domain = labelDomain
    val fDomain = featuresDomain

    /**
      * Predict [[RankLabel]]
      * @param l label
      * @return prediction tensor
      */
    def classify(l: label) = {
      classifier.classification(l.feature.value).prediction
    }

    /**
      * Predict from feature vector
      * @param l feature vector
      * @return prediction tensor
      */
    def classify(l: Tensor1) = {
      classifier.classification(l).prediction
    }

    /**
      * Classifies document into tuples of labelname, sentences, position in sentence, % location in document
      * @param d document to classify
      * @param threshold threshold prediction should be over to return
      * @return list of labelname, sentences, position in sentence, % location in document
      */
    private def classify(d: Document, threshold : Double = 0.5): Seq[(String, String, Int, Double)] = {
      val labels = docToFeature(d, Seq(labelDomain.categories.head))

      labels.flatMap { l =>

        val classifications = classifier.classification(l.feature.value).prediction.toArray
          .zipWithIndex.map { p => (p._2, p._1, l.sentence) }

        classifications.filter(l => sigmoid(l._2) > threshold).map { p =>

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

    def confidenceScore(threshold : Double, prob : Double) : Int = {
      val oneThird = (1.0-threshold) / 3
      val thresholds = (0 until 3).map{ i => threshold + (i*oneThird)}.zipWithIndex
      thresholds.filter{ t => prob >= t._1 }.last._2
    }

    /**
      * Classifies a [[Record]] given a threshold
      * @param record Record to predict
      * @param threshold threshold prediction should be over to return
      * @return Sequence of predicted metadata
      */
    def getMetaData(record : Record, threshold : Double) : Seq[Metadata] = {
      val (d, _) = pdf2Doc.fromString(record.content, record.filename)
      classify(d, threshold).map { case (label, sentence, location, prob) =>
        val split = label.split(":", 2)
        val (labelName, value) = (split.head, split.last)
        val score = confidenceScore(threshold, prob)
        Metadata(record.id.toString, labelName, value, sentence, location, prob, confidenceLevel = score)
      }
    }

  }

}
