package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.Factorie.{DiscreteDomain, _}
import cc.factorie.app.classify.backend.{MulticlassClassifier, RandomForestMulticlassTrainer}
import cc.factorie.app.classify.{BatchOptimizingLinearVectorClassifierTrainer, LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, SVMLinearVectorClassifierTrainer}
import cc.factorie.app.nlp.Document
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la.{SparseIndexedTensor, SparseTensor1}
import cc.factorie.optimize.{AdaGradRDA, L2Regularization, LBFGS}
import cc.factorie.variable.{CategoricalLabeling, VectorDomain, VectorVariable}
import org.datakind.ci.pdfestrian.scripts.Aid

import scala.io.Source
import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class BiomeExtractor {
  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  object BiomeLabelDomain extends CategoricalDomain[String]

  class BiomeLabel(label : String, val feature : BiomeFeatures) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = BiomeLabelDomain
  }

  object BiomeFeaturesDomain extends VectorDomain {
    override type Value = SparseTensor1
    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(TfIdf.featureSize)
  }
  class BiomeFeatures(st1 : SparseTensor1) extends VectorVariable(st1) {//BinaryFeatureVectorVariable[String] {
    def domain = BiomeFeaturesDomain
   //override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(pl : Document, label : String) : BiomeLabel = {
    /*val features = new BiomeFeatures()
    for(e <- pl.sentences; w <- e.tokens) {
      val current = clean(w.string)
      if(current.length > 0 && current.count(_.isLetter) > 0 && !stopWords.contains(current))
        features += "UNIGRAM="+current   // Convert to td-idf weight instead!
      /*if(w.hasNext) {
        val next = clean(w.next.string)
        features += "BIGRAM=" + current + "+" + next
      }*/
    }*/
    val f = TfIdf(pl)
    //val vector = new SparseTensor1(TfIdf.featureSize)
    //vector(0) = f(TfIdf.wordCounts("mangrov")._2)
    //vector(1) = f(TfIdf.wordCounts("mangrov")._2)
    val features = new BiomeFeatures(f)//TfIdf(pl))
    new BiomeLabel(label, features)
  }

  def testAccuracy(testData : Seq[BiomeLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val correct = testData.count{ td => classifier.classification(td.feature.value).bestLabelIndex == td.target.intValue}
    println(evaluate(testData,classifier))
    correct.toDouble/testData.length
  }

  def evaluate(testData : Seq[BiomeLabel], classifier : MulticlassClassifier[Tensor1]) : String = {
    val trueCounts = new Array[Int](BiomeLabelDomain.size)
    val correctCounts = new Array[Int](BiomeLabelDomain.size)
    val predictedCounts = new Array[Int](BiomeLabelDomain.size)

    for(data <- testData) {
      val prediction = classifier.classification(data.feature.value).bestLabelIndex
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
    MulticlassClassifier[Tensor1] = {
    //val classifier2 = new RandomForestMulticlassTrainer(100,100,100).train(trainData, (l : BiomeLabel) => l.feature, (l : BiomeLabel) => 1.0)
    val optimizer = new LBFGS with L2Regularization {
      variance = l2
    }
    val rda = new AdaGradRDA(l1 = l2)
    val trainer = new OnlineOptimizingLinearVectorClassifierTrainer(optimizer = rda)//(l2 = l2)//(optimizer = rda)//, maxIterations = 15)//(optimizer = optimizer)//(l2 = l2)
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

    val data = Aid.load(args.head).toArray.flatMap{ a =>
        extractor.aidToFeature(a)
    }
    println(PorterStemmer("mangrov"))
    val aids = Aid.load(args.head).toArray
    val tm = aids.filter(a => a.biome.isDefined && a.biome.get.biome.trim == "T_M").map { a =>
      println(a.pdf.filename)
      val feature = extractor.aidToFeature(a)
      if(feature.isDefined) {
        val feat = feature.get.feature.value.asInstanceOf[SparseTensor1]
        println(feat(TfIdf.wordCounts("mangrov")._2))
        if(a.interv.isDefined) {
          println(a.interv.get.Int_area )
        } else println("")
        if(a.biome.isDefined) {
          println(a.biome )
        } else println("")
        feat(TfIdf.wordCounts("mangrov")._2)
      } else 0.0
    }
    println("other")
    val other = aids.filter(a => a.biome.isDefined && a.biome.get.biome.trim != "T_M").map { a =>
      println(a.pdf.filename)
      val feature = extractor.aidToFeature(a)
      if(feature.isDefined) {
        val feat = feature.get.feature.value.asInstanceOf[SparseTensor1]
        println(feat(TfIdf.wordCounts("mangrov")._2))
        if(a.interv.isDefined) {
          println(a.interv.get.Int_area )
        } else println("")
        if(a.biome.isDefined) {
          println(a.biome )
        } else println("")
        feat(TfIdf.wordCounts("mangrov")._2)
      } else 0.0
    }
    println("man: " + tm.sum.toDouble/tm.length)
    println("non man: " + other.sum.toDouble/other.length)

    val trainLength = (data.length.toDouble * 0.8).toInt
    val testLength = data.length - trainLength
    val trainData = data.take(trainLength)
    val testData = data.takeRight(testLength)
    //extractor.train(trainData, testData, l2 = 0.5)

    for(d <- 0.01 until 100.0 by 0.001) {
      println("l2=" + d)
      extractor.train(trainData, testData, l2 = d)
    }
  }

}
