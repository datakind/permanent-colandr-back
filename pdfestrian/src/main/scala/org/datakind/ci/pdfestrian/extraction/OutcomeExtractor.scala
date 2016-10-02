package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend.{C45DecisionTreeTrainer, DecisionTreeMulticlassTrainer, MulticlassClassifier, RandomForestMulticlassTrainer}
import cc.factorie.app.nlp.Document
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la.{DenseTensor1, SparseIndexedTensor, SparseTensor1, Tensor1}
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq}

import scala.collection.mutable.ArrayBuffer
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

  class OutcomeLabel(label : String, val feature : OutcomeFeatures, val name : String = "", labels : Array[String], val aid : AidSeq, val doc : Document) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = OutcomeLabelDomain
    def multiLabel : DenseTensor1 = {
      val dt = new DenseTensor1(OutcomeLabelDomain.size)
      for(l <- labels) {
        dt(OutcomeLabelDomain.index(l)) = 1.0
      }
      dt
    }

  }

  object OutcomeFeaturesDomain extends VectorDomain {
    override type Value = SparseTensor1
    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(CombinedFeature.featureSize)
  }
  class OutcomeFeatures(st1 : SparseTensor1) extends VectorVariable(st1) {//BinaryFeatureVectorVariable[String] {
  def domain = OutcomeFeaturesDomain
    //override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(aid : AidSeq, pl : Document, labels : Array[String]) : OutcomeLabel = {
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
    val f = CombinedFeature(pl) //Word2Vec(pl)
    //val vector = new SparseTensor1(TfIdf.featureSize)
    //vector(0) = f(TfIdf.wordCounts("mangrov")._2)
    //vector(1) = f(TfIdf.wordCounts("mangrov")._2)
    val features = new OutcomeFeatures(f)//TfIdf(pl))
    for(l <- labels) {
      new OutcomeLabel(l, features, pl.name, labels, aid, pl)
    }
    new OutcomeLabel(labels.head, features, pl.name, labels, aid, pl)
  }

  def testAccuracy(testData : Seq[OutcomeLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val (eval, score) = evaluate(testData,classifier)
    println(eval)
    score
  }
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def evaluate(testData : Seq[OutcomeLabel], classifier : MulticlassClassifier[Tensor1]) : (String,Double) = {
    val trueCounts = new Array[Int](OutcomeLabelDomain.size)
    val correctCounts = new Array[Int](OutcomeLabelDomain.size)
    val predictedCounts = new Array[Int](OutcomeLabelDomain.size)

    for(data <- testData) {
      val prediction = classifier.classification(data.feature.value).prediction
      //for(i <- 0 until prediction.dim1) {
      //  prediction(i) = sigmoid(prediction(i))
      //}
      val predictedValues = new ArrayBuffer[Int]()
      for(i <- 0 until prediction.dim1) {
        if(prediction(i) > 0.05) predictedValues += i
        //if(sigmoid(prediction(i)) > 0.5) predictedValues += i
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
    val each = OutcomeLabelDomain.indices.map{ i =>
      val brec = if(predictedCounts(i) == 0) 0.0 else correctCounts(i).toDouble/predictedCounts(i).toDouble * 100.0
      val bec = if(trueCounts(i) == 0) 0.0 else correctCounts(i).toDouble/trueCounts(i).toDouble * 100.0
      val bf1 = if(bec + bec == 0) 0.0 else (2.0 * brec * bec) / (brec + bec)
      f"${OutcomeLabelDomain(i).category}\t$brec%2.2f\t$bec%2.2f\t$bf1%2.2f\t${correctCounts(i)}\t${predictedCounts(i)}\t${trueCounts(i)}"
    }.mkString("\n")
    ("Category:\tPrecision\tRecall\tCorrect\tPredicted\tTrue\n" + total + each, f1)
  }

  def l2f(l : OutcomeLabel) = l.feature

  def train(trainData : Seq[OutcomeLabel], testData : Seq[OutcomeLabel], l2 : Double) :
  (MulticlassClassifier[Tensor1], Double) = {
    //val classifier = new DecisionTreeMulticlassTrainer(new C45DecisionTreeTrainer).train(trainData, (l : BiomeLabel) => l.feature, (l : BiomeLabel) => 1.0)
    //val optimizer = new LBFGS// with L2Regularization //
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(OutcomeLabelDomain.size, OutcomeFeaturesDomain.dimensionSize, (l : OutcomeLabel) => l.feature)/*(objective = new SigmoidalLoss().asInstanceOf[OptimizableObjectives.Multiclass]) {
      override def examples[L<:LabeledDiscreteVar,F<:VectorVar](classifier:LinearVectorClassifier[L,F], labels:Iterable[L], l2f:L=>F, objective:Multiclass): Seq[Example] =
        labels.toSeq.map(l => new PredictorExample(classifier, l2f(l).value, l.target.value, objective))//, weight(l.target.intValue)))
    }*/
    val optimizer = new LBFGS with L2Regularization {
      variance = 1000 // LDA
      //variance = 2.5 // tfidf
    }
    //val trainer = new BatchTrainer(classifier.parameters, optimizer)
    val trainer = new OnlineTrainer(classifier.parameters, optimizer = rda)// maxIterations = 2)
    val trainExamples = trainData.map{ td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new HingeLoss, if(td.multiLabel.sum == 1.0) 10.0 else 1.0)
    }

    while(!trainer.isConverged)
      trainer.processExamples(trainExamples)
    //val classifier = trainer.train(trainData, l2f)
    println("Train Acc: ")
    testAccuracy(trainData, classifier)
    println("Test Acc: ")
    (classifier, testAccuracy(testData,classifier))
  }

  def aidToFeature(aid : AidSeq) : Option[OutcomeLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => None
      case Some(d) =>
        aid.outcome match {
          case b if b.isEmpty => None
          case b if b.length == 1 && b.head.Outcome == "NA" => None
          case b => Some(docToFeature(aid,d._1,b.map{_.Outcome}.distinct.toArray))
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
    val distribution = AidSeq.load(args.head).toArray.filter( o => o.outcome.nonEmpty && o.outcome.head.Outcome != "NA").flatMap(_.outcome).groupBy(_.Outcome).map{ b => b._1 -> b._2.length}
    val count = AidSeq.load(args.head).toArray.filter(_.outcome.nonEmpty).flatMap(_.outcome).length
    val extractor = new OutcomeExtractor(distribution, count)

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
    val (klass, reg) = /*(0.00005 to 0.005 by 0.00003)*/(0.00001 to 0.001 by 0.00001).map{ e => (extractor.train(trainData,testData,e),e) }.maxBy(_._1._2)
    val (classifier, f1) = klass
    println(f1)
    println(extractor.evaluate(testData, classifier)._1)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value
    for(label <- extractor.OutcomeLabelDomain) {
      println(label.category)
      println((0 until TfIdf.featureSize).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) }.mkString("\t"))
    }
    for(label <- extractor.OutcomeLabelDomain) {
      print(label.category + "\t")
      //println((0 until weights.dim1).map{ i => i -> weights(i,label.intValue)}.sortBy(-_._2).take(20).map{ i => TfIdf.words(i._1) + "\t" + i._2}.mkString("\n"))
      println((0 until TfIdf.featureSize).map{ i => i -> weights(i,label.intValue)}.filter(_._2 != 0.0).sortBy(-_._2).take(30).map{ i => TfIdf.words(i._1) + "," + i._2 }.mkString("\t"))
    }
    val matrix = new DenseTensor2(extractor.OutcomeLabelDomain.length, extractor.OutcomeLabelDomain.length)
    for(d <- testData) {
      val klass = classifier.classification(d.feature.value).prediction.toArray.zipWithIndex.filter(l => l._1 >= 0.05).map{i => i._2}
      val labels = d.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map{_._2}
      for(l <- labels) {
        if(!klass.contains(l)) {
          for(k <- klass; if !labels.contains(k)) {
            matrix(l,k) += 1
          }
        }
      }
    }
    println("\t" + extractor.OutcomeLabelDomain.map{_.category}.mkString("\t"))
    for(i <- extractor.OutcomeLabelDomain) {
      print(i.category + "\t")
      println(extractor.OutcomeLabelDomain.map{j => matrix(i.intValue,j.intValue)}.mkString("\t"))
    }

    val corrMatrix = new DenseTensor2(extractor.OutcomeLabelDomain.length, extractor.OutcomeLabelDomain.length)
    for(d <- trainData ++ testData) {
      val labels = d.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map {
        _._2
      }
      for (l <- labels; k <- labels; if l != k) {
        corrMatrix(l, k) += 1
      }
      if(labels.length == 1) {
        corrMatrix(labels.head, labels.head) += 1
      }
    }
    for(l <- 0 until corrMatrix.dim1) {
      val sum = (0 until corrMatrix.dim2).map{ i => corrMatrix(l,i)}.sum
      for(i <- 0 until corrMatrix.dim2) corrMatrix(l,i) /= sum
    }

    println("Corr")
    println("\t" + extractor.OutcomeLabelDomain.map{_.category}.mkString("\t"))
    for(i <- extractor.OutcomeLabelDomain) {
      print(i.category + "\t")
      println(extractor.OutcomeLabelDomain.map{j => corrMatrix(i.intValue,j.intValue)}.mkString("\t"))
    }


    errorWords(testData, classifier, extractor.OutcomeLabelDomain.categories)
    println("\n\n\n\n")
    errorSentences(testData,classifier,extractor.OutcomeLabelDomain.categories)

    def errorWords(testSet : Seq[extractor.OutcomeLabel], classifier : MulticlassClassifier[Tensor1], domain : Seq[String]) = {
      val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value
      for(testExample <- testSet) {
        val klass = classifier.classification(testExample.feature.value).prediction.toArray.zipWithIndex.filter(l => l._1 >= 0.05).map{i => i._2}
        val allPredicted = klass.map{ domain }.mkString(",")

        val labels = testExample.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map{_._2}
        for(k <- klass; if !labels.contains(k) ) {
          val klassFeatures = (0 until TfIdf.featureSize).filter( i => testExample.feature.value(i) != 0.0).map{ w => w -> weights(w,k) * testExample.feature.value(w) }.sortBy(-_._2)
          val words = klassFeatures.map{ case (i,f) => TfIdf.words(i) -> f}.take(10)
          val trueLabels = testExample.aid.outcome.map(a => a.Outcome).distinct.mkString(",")
          for(w <- words) {
            println(testExample.aid.index + "\t" + testExample.aid.bib.Authors + "\t" + testExample.name + "\t" + domain(k) + "\t" + allPredicted + "\t" + trueLabels + "\t" + w._1 + "\t" + w._2)
          }
        }
      }
    }
    def errorSentences(testSet : Seq[extractor.OutcomeLabel], classifier : MulticlassClassifier[Tensor1], domain : Seq[String]) = {
      val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value
      for(testExample <- testSet) {
        val klass = classifier.classification(testExample.feature.value).prediction.toArray.zipWithIndex.filter(l => l._1 >= 0.05).map{i => i._2}
        val allPredicted = klass.map{ domain }.mkString(",")

        val labels = testExample.multiLabel.toArray.zipWithIndex.filter(_._1 == 1.0).map{_._2}
        for(k <- klass; if !labels.contains(k) ) {
          val klassFeatures = (0 until TfIdf.featureSize).filter( i => testExample.feature.value(i) != 0.0).map{ w => w -> weights(w,k) * testExample.feature.value(w) }.sortBy(-_._2)
          val words = klassFeatures.map{ case (i,f) => TfIdf.words(i) -> f}
          val sentences = FindSentences.find(testExample.doc,words.toArray)
          val trueLabels = testExample.aid.outcome.map(a => a.Outcome).distinct.mkString(",")
          for(s <- sentences) {
            println(testExample.aid.index + "\t" + testExample.aid.bib.Authors + "\t" + testExample.name + "\t" + domain(k) + "\t" + allPredicted + "\t" + trueLabels + "\t" + s)
          }
        }
      }
    }

  }

}
