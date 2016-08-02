package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.Factorie._
import cc.factorie.app.classify.{LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, SVMLinearVectorClassifierTrainer}
import cc.factorie.app.nlp.Document
import cc.factorie.optimize.AdaGradRDA
import cc.factorie.variable.{BinaryFeatureVectorVariable, CategoricalDomain, CategoricalLabeling, CategoricalVariable}
import org.datakind.ci.pdfestrian.scripts.Aid

import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class BiomeExtractor {
  implicit val rand = new Random()


  object BiomeLabelDomain extends CategoricalDomain[String]

  class BiomeLabel(label : String, val feature : BiomeFeatures) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = BiomeLabelDomain
  }

  object BiomeFeaturesDomain extends CategoricalVectorDomain[String]
  class BiomeFeatures() extends BinaryFeatureVectorVariable[String] {
    def domain = BiomeFeaturesDomain
    override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(pl : Document, label : String) : BiomeLabel = {
    val features = new BiomeFeatures()
    for(e <- pl.sentences; w <- e.tokens) {
      val current = clean(w.string)
      features += "UNIGRAM="+current
      if(w.hasNext) {
        val next = clean(w.next.string)
        features += "BIGRAM=" + current + "+" + next
      }
    }
    new BiomeLabel(label, features)
  }

  def testAccuracy(testData : Seq[BiomeLabel], classifier : LinearVectorClassifier[BiomeLabel, BiomeFeatures]) : Double = {
    val correct = testData.count{ td => classifier.bestLabelIndex(td) == td.target.intValue}
    println(evaluate(testData,classifier))
    correct.toDouble/testData.length
  }

  def evaluate(testData : Seq[BiomeLabel], classifier : LinearVectorClassifier[BiomeLabel, BiomeFeatures]) : String = {
    val trueCounts = new Array[Int](BiomeLabelDomain.size)
    val correctCounts = new Array[Int](BiomeLabelDomain.size)
    val predictedCounts = new Array[Int](BiomeLabelDomain.size)

    for(data <- testData) {
      val prediction = classifier.bestLabelIndex(data)
      val trueValue = data.target.intValue
      trueCounts(trueValue) += 1
      predictedCounts(prediction) += 1
      if(trueValue == prediction) {
        correctCounts(trueValue) += 1
      }
    }
    val trueCount = trueCounts.sum
    val correctCount = correctCounts.sum
    val predictedCount = predictedCounts.sum
    val prec = correctCount.toDouble/predictedCount.toDouble * 100.0
    val rec = correctCount.toDouble/trueCount.toDouble * 100.0
    val f1 = (2.0 * prec * rec) / (prec + rec)
    val total = f"Total\t$prec%2.2f\t$rec%2.2f\t$f1%2.2f\t$correctCount\t$predictedCount\t$trueCount\n"
    val each = BiomeLabelDomain.indices.map{ i =>
      val brec = if(predictedCounts(i) == 0) 0.0 else correctCounts(i).toDouble/predictedCounts(i).toDouble * 100.0
      val bec = if(trueCounts(i) == 0) 0.0 else correctCounts(i).toDouble/trueCounts(i).toDouble * 100.0
      val bf1 = if(bec + bec == 0) 0.0 else (2.0 * brec * bec) / (brec + bec)
      f"${BiomeLabelDomain(i).category}\t$brec%2.2f\t$bec%2.2f\t$bf1%2.2f\t${correctCounts(i)}\t${predictedCounts(i)}\t${trueCounts(i)}"
    }.mkString("\n")
    "Category:\tPrecision\tRecall\tCorrect\tPredicted\tTrue\n" + total + each
  }

  def l2f(l : BiomeLabel) = l.feature

  def train(trainData : Seq[BiomeLabel], testData : Seq[BiomeLabel], l2 : Double) :
    LinearVectorClassifier[BiomeLabel, BiomeFeatures] = {
    val trainer = new SVMLinearVectorClassifierTrainer(l2 = l2)
    val classifier = trainer.train(trainData, l2f)
    println("Train Acc: " + testAccuracy(trainData,classifier) )
    println("Test Acc: " + testAccuracy(testData,classifier) )
    classifier
  }

  def aidToFeature(aid : Aid) : Option[BiomeLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => None
      case Some(d) =>
        aid.biome match {
          case None => None
          case Some(b) => Some(docToFeature(d._1,b.biome))
        }
    }
  }

}
object BiomeExtractor {

  def main(args: Array[String]): Unit = {
    val extractor = new BiomeExtractor

    val data = Aid.load(args.head).flatMap{ a =>
        extractor.aidToFeature(a)
    }
    val trainLength = (data.length.toDouble * 0.8).toInt
    val testLength = data.length - trainLength
    val trainData = data.take(trainLength)
    val testData = data.takeRight(testLength)
    for(d <- 0.1 until 20.0 by 0.1) {
      println("l2=" + d)
      extractor.train(trainData, testData, l2 = d)
    }
  }

}
