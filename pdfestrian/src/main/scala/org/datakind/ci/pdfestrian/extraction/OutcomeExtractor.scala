package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend.{C45DecisionTreeTrainer, DecisionTreeMulticlassTrainer, MulticlassClassifier, RandomForestMulticlassTrainer}
import cc.factorie.app.classify.{BatchOptimizingLinearVectorClassifierTrainer, LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, SVMLinearVectorClassifierTrainer}
import cc.factorie.app.nlp.Document
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la.{SparseIndexedTensor, SparseTensor1, Tensor1}
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.scripts.Aid

import scala.io.Source
import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class OutcomeExtractor(distMap : Map[String,Int], length : Int) {

  lazy val weight = OutcomeLabelDomain.map{ bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = distMap(name)
    val tw = length.toDouble/count.toDouble
    val newW = tw //if(tw < 15.0) 1.0 else tw*100
    intval -> newW
  }.sortBy(_._1).map{_._2}.toArray

  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  object OutcomeLabelDomain extends CategoricalDomain[String]

  class OutcomeLabel(label : String, val feature : OutcomeFeatures, val name : String = "") extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = OutcomeLabelDomain
  }

  object OutcomeFeaturesDomain extends VectorDomain {
    override type Value = SparseTensor1
    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(TfIdf.featureSize)
  }
  class OutcomeFeatures(st1 : SparseTensor1) extends VectorVariable(st1) {//BinaryFeatureVectorVariable[String] {
  def domain = OutcomeFeaturesDomain
    //override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(pl : Document, label : String) : OutcomeLabel = {
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
    val features = new OutcomeFeatures(f)//TfIdf(pl))
    new OutcomeLabel(label, features, pl.name)
  }

  def testAccuracy(testData : Seq[OutcomeLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val correct = testData.count{ td =>
      val classification = classifier.classification(td.feature.value)
      classification.bestLabelIndex == td.target.intValue
    }
    println(evaluate(testData,classifier))
    correct.toDouble/testData.length
  }

  def evaluate(testData : Seq[OutcomeLabel], classifier : MulticlassClassifier[Tensor1]) : String = {
    val trueCounts = new Array[Int](OutcomeLabelDomain.size)
    val correctCounts = new Array[Int](OutcomeLabelDomain.size)
    val predictedCounts = new Array[Int](OutcomeLabelDomain.size)

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
    val each = OutcomeLabelDomain.indices.map{ i =>
      val brec = if(predictedCounts(i) == 0) 0.0 else correctCounts(i).toDouble/predictedCounts(i).toDouble * 100.0
      val bec = if(trueCounts(i) == 0) 0.0 else correctCounts(i).toDouble/trueCounts(i).toDouble * 100.0
      val bf1 = if(bec + bec == 0) 0.0 else (2.0 * brec * bec) / (brec + bec)
      f"${OutcomeLabelDomain(i).category}\t$brec%2.2f\t$bec%2.2f\t$bf1%2.2f\t${correctCounts(i)}\t${predictedCounts(i)}\t${trueCounts(i)}"
    }.mkString("\n")
    "Category:\tPrecision\tRecall\tCorrect\tPredicted\tTrue\n" + total + each
  }

  def l2f(l : OutcomeLabel) = l.feature

  def train(trainData : Seq[OutcomeLabel], testData : Seq[OutcomeLabel], l2 : Double) :
  MulticlassClassifier[Tensor1] = {
    //val classifier = new DecisionTreeMulticlassTrainer(new C45DecisionTreeTrainer).train(trainData, (l : BiomeLabel) => l.feature, (l : BiomeLabel) => 1.0)
    val optimizer = new LBFGS with L2Regularization {
      variance = 10
    }
    val rda = new AdaGradRDA(l2 = l2)
    val trainer = new BatchOptimizingLinearVectorClassifierTrainer(optimizer = optimizer) {
      override def examples[L<:LabeledDiscreteVar,F<:VectorVar](classifier:LinearVectorClassifier[L,F], labels:Iterable[L], l2f:L=>F, objective:Multiclass): Seq[Example] =
        labels.toSeq.map(l => new PredictorExample(classifier, l2f(l).value, l.target.intValue, objective, weight(l.target.intValue)))
    }
    val classifier = trainer.train(trainData, l2f)
    println("Train Acc: " + testAccuracy(trainData,classifier) )
    println("Test Acc: " + testAccuracy(testData,classifier) )
    classifier
  }

  def aidToFeature(aid : Aid) : Option[OutcomeLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => None
      case Some(d) =>
        aid.outcome match {
          case None => None
          case Some(b) if b.Outcome == "NA" => None
          case Some(b) => Some(docToFeature(d._1,b.Outcome))
        }
    }
  }

}
object OutcomeExtractor {

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
    val distribution = Aid.load(args.head).toArray.filter( o => o.outcome.isDefined && o.outcome.get.Outcome != "NA").groupBy(_.outcome.get.Outcome).map{ b => b._1 -> b._2.length}
    val count = Aid.load(args.head).toArray.count(_.biome.isDefined)
    val extractor = new OutcomeExtractor(distribution, count)

    val data = Aid.load(args.head).toArray.flatMap{ a =>
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
    val classifier = extractor.train(trainData,testData,0.00000005)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value
    for(label <- extractor.OutcomeLabelDomain) {
      println(label.category)
      println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) }.mkString("\t"))
    }
    for(label <- extractor.OutcomeLabelDomain) {
      print(label.category + "\t")
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) }.mkString("\t"))
    }
    val matrix = new DenseTensor2(extractor.OutcomeLabelDomain.length, extractor.OutcomeLabelDomain.length)
    for(d <- testData) {
      val klass = classifier.classification(d.feature.value).bestLabelIndex
      if(d.intValue != klass) {
        matrix(d.intValue, klass) += 1
      }
    }
    println("\t" + extractor.OutcomeLabelDomain.map{_.category}.mkString("\t"))
    for(i <- extractor.OutcomeLabelDomain) {
      print(i.category + "\t")
      println(extractor.OutcomeLabelDomain.map{j => matrix(i.intValue,j.intValue)}.mkString("\t"))
    }

    val mat_liv_std = extractor.OutcomeLabelDomain.find(_.category=="mat_liv_std").get.intValue
    val eco_liv_std = extractor.OutcomeLabelDomain.find(_.category=="eco_liv_std").get.intValue
    for(d <- testData) {
      val klass = classifier.classification(d.feature.value).bestLabelIndex
      if(klass == eco_liv_std && d.intValue == mat_liv_std) println(d.name)
    }




  }

}
