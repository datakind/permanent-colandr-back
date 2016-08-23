package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend._
import cc.factorie.app.classify.{BatchOptimizingLinearVectorClassifierTrainer, LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, SVMLinearVectorClassifierTrainer}
import cc.factorie.app.nlp.Document
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la._
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.util.DoubleAccumulator
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq, Biome}

import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.util.Random


class SigmoidalLoss extends MultivariateOptimizableObjective[Tensor1] {
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
    var objective = 0.0
    val gradient = new SparseIndexedTensor1(prediction.size)
    for (i <- prediction.activeDomain) {
      val sigvalue = sigmoid(prediction(i))
      val diff = sigvalue - label(i)
      val value = -label(i)*prediction(i) + math.log1p(math.exp(prediction(i)))
      objective -= value
      gradient += (i, diff)
    }
    (objective, gradient)
  }
}

class HingeLoss extends MultivariateOptimizableObjective[Tensor1] {

  def valueAndGradient(prediction: Tensor1, label: Tensor1): (Double, Tensor1) = {
    var objective = 0.0
    val gradient = new SparseIndexedTensor1(prediction.size)
    for (i <- prediction.activeDomain) {
      if(prediction(i) < 0.1 && label(i) == 1.0) {
        gradient += (i, 1.0f)
        objective += prediction(i) - 0.1
      } else if(prediction(i) > 0.0 && label(i) == 0.0) {
        gradient += (i, -1.0f)
        objective += - prediction(i)
      }
    }
    (objective, gradient)
  }
}


/**
  * Created by sameyeam on 8/1/16.
  */
class BiomeExtractor(distMap : Map[String,Int], length : Int) {

  lazy val weight = BiomeLabelDomain.map{ bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = distMap(name)
    val tw = length.toDouble/count.toDouble
    val newW = if(tw < 15.0) 1.0 else tw*100
    intval -> newW
  }.sortBy(_._1).map{_._2}.toArray

  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  object BiomeLabelDomain extends CategoricalDomain[String]

  class BiomeLabel(label : String, val feature : BiomeFeatures, val name : String = "", val labels : Seq[String]) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = BiomeLabelDomain
    def multiLabel : DenseTensor1 = {
      val dt = new DenseTensor1(BiomeLabelDomain.size)
      for(l <- labels) {
        dt(BiomeLabelDomain.index(l)) = 1.0
      }
      dt
    }
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

  def docToFeature(pl : Document, labels : Seq[String]) : BiomeLabel = {
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
    val f = TfIdf(pl) //Word2Vec(pl)
    //val vector = new SparseTensor1(TfIdf.featureSize)
    //vector(0) = f(TfIdf.wordCounts("mangrov")._2)
    //vector(1) = f(TfIdf.wordCounts("mangrov")._2)
    val features = new BiomeFeatures(f)//TfIdf(pl))
    for(l <- labels) {
      new BiomeLabel(l,features,pl.name, labels)
    }
    new BiomeLabel(labels.head, features, pl.name, labels)
  }

  def testAccuracy(testData : Seq[BiomeLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val correct = testData.count{ td => classifier.classification(td.feature.value).bestLabelIndex == td.target.intValue}
    println(evaluate(testData,classifier))
    correct.toDouble/testData.length
  }

  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }


  def evaluate(testData : Seq[BiomeLabel], classifier : MulticlassClassifier[Tensor1]) : String = {
    val trueCounts = new Array[Int](BiomeLabelDomain.size)
    val correctCounts = new Array[Int](BiomeLabelDomain.size)
    val predictedCounts = new Array[Int](BiomeLabelDomain.size)

    for(data <- testData) {
      val prediction = classifier.classification(data.feature.value).prediction
      for(i <- 0 until prediction.dim1) {
        prediction(i) = sigmoid(prediction(i))
      }
      val predictedValues = new ArrayBuffer[Int]()
      for(i <- 0 until prediction.dim1) {
        if(prediction(i) >= 0.5) predictedValues += i
      }
      val trueValue = data.multiLabel
      val trueValues = new ArrayBuffer[Int]()
      for(i <- 0 until trueValue.dim1) {
        if(trueValue(i) == 1.0) trueValues += i
      }
      trueValues.foreach{ tv => trueCounts(tv) += 1 }
      predictedValues.foreach{ pv => predictedCounts(pv) += 1 }
      for(p <- predictedValues; if trueValues.contains(p)) {
        correctCounts(p) += 1
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
    //val classifier = new DecisionTreeMulticlassTrainer(new C45DecisionTreeTrainer).train(trainData, (l : BiomeLabel) => l.feature, (l : BiomeLabel) => 1.0)
    //val optimizer = new LBFGS// with L2Regularization //
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(BiomeLabelDomain.size, BiomeFeaturesDomain.dimensionSize, (l : BiomeLabel) => l.feature)/*(objective = new SigmoidalLoss().asInstanceOf[OptimizableObjectives.Multiclass]) {
      override def examples[L<:LabeledDiscreteVar,F<:VectorVar](classifier:LinearVectorClassifier[L,F], labels:Iterable[L], l2f:L=>F, objective:Multiclass): Seq[Example] =
        labels.toSeq.map(l => new PredictorExample(classifier, l2f(l).value, l.target.value, objective))//, weight(l.target.intValue)))
    }*/
    val optimizer = new AdaGrad()
    val trainer = new OnlineTrainer(classifier.parameters, optimizer)
    val trainExamples = trainData.map{ td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new HingeLoss, 1.0)
    }
    val testExamples = trainData.map{ td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new HingeLoss, 1.0)
    }

    for(i <- 0 until 50)
      trainer.processExamples(trainExamples)
    //val classifier = trainer.train(trainData, l2f)
    println("Train Acc: " + testAccuracy(trainData,classifier) )
    println("Test Acc: " + testAccuracy(testData,classifier) )
    classifier
  }

  def aidToFeature(aid : AidSeq) : Option[BiomeLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => None
      case Some(d) =>
        aid.biome match {
          case a : Seq[Biome] if a.isEmpty => None
          case a: Seq[Biome] =>
            Some(docToFeature(d._1,a.map(_.biome).distinct))
        }
    }
  }

}
object BiomeExtractor {

  def main(args: Array[String]): Unit = {
    //println(PorterStemmer("mangrov"))
   /* val aids = Aid.load(args.head).toArray
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
    println("non man: " + other.sum.toDouble/other.length)*/
    val distribution = AidSeq.load(args.head).toArray.filter(_.biome.nonEmpty).flatMap(_.biome).groupBy(_.biome).map{ b => (b._1,b._2.length) }
    val count = AidSeq.load(args.head).toArray.flatMap(_.biome).length
    val extractor = new BiomeExtractor(distribution, count)

    val data = AidSeq.load(args.head).toArray.flatMap{ a =>
      extractor.aidToFeature(a)
    }

    val trainLength = (data.length.toDouble * 0.8).toInt
    val testLength = data.length - trainLength
    val trainData = data.take(trainLength)
    val testData = data.takeRight(testLength)
    //extractor.train(trainData, testData, l2 = 0.5)

    //for(d <- 0.3 until 10.0 by 0.01) {
    //  println("l2=" + d)
    //  extractor.train(trainData, testData, l2 = d)
    //}
    val classifier = extractor.train(trainData,testData,0.0)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value
    /*for(label <- extractor.BiomeLabelDomain) {
      println(label.category)
      println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) }.mkString("\t"))
    }
    for(label <- extractor.BiomeLabelDomain) {
      print(label.category + "\t")
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) }.mkString("\t"))
    }*/
    val matrix = new DenseTensor2(extractor.BiomeLabelDomain.length, extractor.BiomeLabelDomain.length)
    for(d <- testData) {
      val klass = classifier.classification(d.feature.value).bestLabelIndex
      if(d.intValue != klass) {
        matrix(d.intValue, klass) += 1
      }
    }
    println("\t" + extractor.BiomeLabelDomain.map{_.category}.mkString("\t"))
    for(i <- extractor.BiomeLabelDomain) {
      print(i.category + "\t")
      println(extractor.BiomeLabelDomain.map{j => matrix(i.intValue,j.intValue)}.mkString("\t"))
    }

    val T_TSTMBF = extractor.BiomeLabelDomain.find(_.category=="T_TSTMBF").get.intValue
    val T_TSTGSS = extractor.BiomeLabelDomain.find(_.category=="T_TSTGSS").get.intValue
    for(d <- testData) {
      val klass = classifier.classification(d.feature.value).bestLabelIndex
      if(klass == T_TSTMBF && d.intValue == T_TSTGSS) println(d.name)
    }

  }

}
