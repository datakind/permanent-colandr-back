package org.datakind.ci.pdfestrian.extraction

import java.io._

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend._
import cc.factorie.app.classify.{Classification => _, _}
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.la._
import cc.factorie.optimize.{AdaGradRDA, OnlineTrainer, PredictorExample}
import cc.factorie.util.BinarySerializer
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.scripts.AidSeq

import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class Ranker(distMap: Map[String, Int], length: Int) {

  val combinedSent = CombinedSent()

  lazy val weight = labelDomain.map { bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = distMap(name)
    val tw = (length - count).toDouble / count.toDouble
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

  class RankLabel(label: String, val feature: RankFeatures, val name: String = "", val labels: Seq[String], val aid: Option[AidSeq], val doc: Document, val sentence: Sentence) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
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

    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(combinedSent.featureSize)
  }

  class RankFeatures(st1: SparseTensor1) extends VectorVariable(st1) {
    def domain = featuresDomain
  }

  def clean(string: String): String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(aid: Option[AidSeq], pl: Document, labels: Seq[String]): Seq[RankLabel] = {
    if(labels.isEmpty)
      return Seq()
    val sentences = pl.sentences.toArray.filter(_.string.length > 70)
    val length = sentences.length
    sentences.zipWithIndex.map { case (sent, i) =>
      val f = combinedSent(sent, i.toDouble / length.toDouble, pl.name)
      val features = new RankFeatures(f)
      for (l <- labels) {
        new RankLabel(l, features, pl.name, labels, aid, pl, sent)
      }
      new RankLabel(labels.headOption.getOrElse(labelDomain.categories.head), features, pl.name, labels, aid, pl, sent)
    }
  }

  def testAccuracy(testData: Seq[RankLabel], classifier: MulticlassClassifier[Tensor1]): Double = {
    val (eval, f1) = evaluate(testData, classifier)
    println(eval)
    f1
  }

  def sigmoid(d: Double): Double = {
    1.0 / (1.0f + math.exp(-d))
  }


  def evaluate(testData: Seq[RankLabel], classifier: MulticlassClassifier[Tensor1]): (String, Double) = {
    val trueCounts = new Array[Int](labelDomain.size)
    val correctCounts = new Array[Int](labelDomain.size)
    val predictedCounts = new Array[Int](labelDomain.size)

    for (data <- testData) {
      val prediction = classifier.classification(data.feature.value).prediction
      val predictedValues = new ArrayBuffer[Int]()
      for (i <- 0 until prediction.dim1) {
        if (sigmoid(prediction(i)) > 0.5) predictedValues += i
      }
      val trueValue = data.multiLabel
      val trueValues = new ArrayBuffer[Int]()
      for (i <- 0 until trueValue.dim1) {
        if (trueValue(i) == 1.0) trueValues += i
      }
      trueValues.foreach { tv => trueCounts(tv) += 1 }
      predictedValues.foreach { pv => predictedCounts(pv) += 1 }
      for (p <- predictedValues; if trueValues.contains(p)) {
        correctCounts(p) += 1
      }
    }
    val trueCount = trueCounts.sum
    val correctCount = correctCounts.sum
    val predictedCount = predictedCounts.sum
    val prec = correctCount.toDouble / predictedCount.toDouble * 100.0
    val rec = correctCount.toDouble / trueCount.toDouble * 100.0
    val f1 = (2.0 * prec * rec) / (prec + rec)
    val total = f"Total\t$prec%2.2f\t$rec%2.2f\t$f1%2.2f\t$correctCount\t$predictedCount\t$trueCount\n"
    val each = labelDomain.indices.map { i =>
      val brec = if (predictedCounts(i) == 0) 0.0 else correctCounts(i).toDouble / predictedCounts(i).toDouble * 100.0
      val bec = if (trueCounts(i) == 0) 0.0 else correctCounts(i).toDouble / trueCounts(i).toDouble * 100.0
      val bf1 = if (bec + bec == 0) 0.0 else (2.0 * brec * bec) / (brec + bec)
      f"${labelDomain(i).category}\t$brec%2.2f\t$bec%2.2f\t$bf1%2.2f\t${correctCounts(i)}\t${predictedCounts(i)}\t${trueCounts(i)}"
    }.mkString("\n")
    ("Category:\tPrecision\tRecall\tCorrect\tPredicted\tTrue\n" + total + each, f1)
  }

  def l2f(l: RankLabel) = l.feature


  def train(trainData: Seq[RankLabel], testData: Seq[RankLabel], l2: Double):
  (LinearVectorClassifier[RankLabel, RankFeatures], Double) = {
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(labelDomain.size, featuresDomain.dimensionSize, (l: RankLabel) => l.feature)
    val trainer = new OnlineTrainer(classifier.parameters, optimizer = rda, maxIterations = 3)
    val trainExamples = trainData.map { td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new LossFunctions.SigmoidalLoss)//(dWeight))
    }
    val shuffed = Random.shuffle(trainExamples)

    while (!trainer.isConverged)
      trainer.processExamples(shuffed)
    println("Train Acc: ")
    testAccuracy(trainData, classifier)
    println("Test Acc: ")
    (classifier, testAccuracy(testData, classifier))
  }

  def aidToFeature(aid: AidSeq)(f: (AidSeq => Seq[String])): Seq[RankLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => Seq()
      case Some(d) =>
        docToFeature(Some(aid), d._1, f(aid))
    }
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

    def classify(d: Document): Seq[(String, String, Int, Double)] = {
      val labels = docToFeature(None, d, Seq(labelDomain.categories.head))
      labels.flatMap { l =>
        classifier.classification(l.feature.value).prediction.toArray
          .zipWithIndex.map { p => (p._2, p._1, l.sentence) }
          .filter(l => sigmoid(l._2) > 0.45).map { p =>
          (domain(p._1).category, l.sentence.tokensString(" "), l.sentence.indexInSection, sigmoid(p._2))
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
  }

}

case class SentenceClassifications(index: Int, text: String, classes: Seq[(String, Double)])

object Ranker {
  def deserialize(loc: String): Ranker#Classifier = {
    val dis = new DataInputStream(new BufferedInputStream(getClass.getResourceAsStream(loc)))
    val extractor = new Ranker(Map[String, Int](), 0)
    BinarySerializer.deserialize(extractor.labelDomain, dis)
    val model = extractor.createClassifier()
    BinarySerializer.deserialize(model.classifier, dis)
    model
  }
}

class RankTrainer(metaData: (AidSeq => Seq[String])) {
  def sigmoid(d: Double): Double = {
    1.0 / (1.0f + math.exp(-d))
  }

  def train(aidLoc: String, saveTo: String): Unit = {
    val distribution = AidSeq.load(aidLoc).toArray.flatMap(aid => metaData(aid).distinct).groupBy(a => a).map { a => a._1 -> a._2.length }
    val count = AidSeq.load(aidLoc).toArray.count(aid => metaData(aid).nonEmpty)
    val extractor = new Ranker(distribution, count)

    val data = AidSeq.load(aidLoc).toArray

    val trainLength = (data.length.toDouble * 0.8).toInt
    val testLength = data.length - trainLength
    val trainData = data.take(trainLength).flatMap { a => extractor.aidToFeature(a)(metaData) }
    val testData = data.takeRight(testLength).flatMap(a => extractor.aidToFeature(a)(metaData))
    val testDocuments = data.takeRight(testLength).map { a => extractor.aidToFeature(a)(metaData) }

    val (klass, reg) = (0.0000005 to 0.000005 by 0.0000005).map { e => (extractor.train(trainData, testData, e), e) }.maxBy(_._1._2)
    val (classifier, f1) = klass

    val dos = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(saveTo)))
    BinarySerializer.serialize(extractor.labelDomain, dos)
    BinarySerializer.serialize(classifier, dos)
    dos.flush()
    dos.close()

    println(f1)
    println(extractor.evaluate(testData, classifier)._1)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_, _]].weights.value

    val matrix = new DenseTensor2(extractor.labelDomain.length, extractor.labelDomain.length)
    for (d <- testData) {
      val klass = classifier.classification(d.feature.value).prediction.toArray.zipWithIndex.filter(l => sigmoid(l._1) >= 0.5).map { i => i._2 }
      val labels = d.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map {
        _._2
      }
      for (l <- labels) {
        if (!klass.contains(l)) {
          for (k <- klass; if !labels.contains(k)) {
            matrix(l, k) += 1
          }
        }
      }
    }

    println("\t" + extractor.labelDomain.map {
      _.category
    }.mkString("\t"))
    for (i <- extractor.labelDomain) {
      print(i.category + "\t")
      println(extractor.labelDomain.map { j => matrix(i.intValue, j.intValue) }.mkString("\t"))
    }
    val corrMatrix = new DenseTensor2(extractor.labelDomain.length, extractor.labelDomain.length)
    for (d <- trainData ++ testData) {
      val labels = d.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map {
        _._2
      }
      for (l <- labels; k <- labels; if l != k) {
        corrMatrix(l, k) += 1
      }
      if (labels.length == 1) {
        corrMatrix(labels.head, labels.head) += 1
      }
    }
    for (l <- 0 until corrMatrix.dim1) {
      val sum = (0 until corrMatrix.dim2).map { i => corrMatrix(l, i) }.sum
      for (i <- 0 until corrMatrix.dim2) corrMatrix(l, i) /= sum
    }

    println("Corr")
    println("\t" + extractor.labelDomain.map {
      _.category
    }.mkString("\t") + "\t" + "Alone")
    for (i <- extractor.labelDomain) {
      print(i.category + "\t")
      println(extractor.labelDomain.map { j => corrMatrix(i.intValue, j.intValue) }.mkString("\t"))
    }
    val sentencesWriter = new BufferedWriter(new FileWriter(new File(saveTo + ".senteces.txt")))
    topSentences(testDocuments.filter(_.nonEmpty), classifier, extractor.labelDomain.categories, sentencesWriter)
    sentencesWriter.flush()
    sentencesWriter.close()
    def topSentences(testSet: Array[Seq[extractor.RankLabel]], classifier: MulticlassClassifier[Tensor1], domain: Seq[String], out : BufferedWriter) = {
      for (testExample <- testSet; if testExample.nonEmpty && testExample.head.aid.isDefined && metaData(testExample.head.aid.get).nonEmpty) {
        val trueLabels = metaData(testExample.head.aid.get).mkString(",")
        val sentences = testExample.flatMap { sent =>
          val klass = classifier.classification(sent.feature.value).prediction.toArray.zipWithIndex
          klass.map { k => (k._2, k._1, sent.sentence) }
        }.groupBy(_._1).map { p => p._1 -> p._2.sortBy(-_._2) }
        sentences.foreach { sent =>
          sent._2.take(10).filter(e => sigmoid(e._2) > 0.50
          ).foreach { example =>
            out.write(testExample.head.aid.get.index + "\t" + testExample.head.aid.get.bib.Authors + "\t" + testExample.head.name + "\t" + domain(sent._1) + "\t" + sigmoid(example._2) + "\t" + trueLabels + "\t" + example._3.string)
            out.write("\n")
          }
        }
      }
    }


  }

}