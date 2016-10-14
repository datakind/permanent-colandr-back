package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend.{LinearMulticlassClassifier, _}
import cc.factorie.app.classify.{Classification => _, _}
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la._
import cc.factorie.model.{DotTemplateWithStatistics2, Parameters}
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.util.DoubleAccumulator
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq, Outcome}

import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.reflect.ClassTag
import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class OutcomeRanker(distMap : Map[String,Int], length : Int) {

  lazy val weight = OutcomeLabelDomain.map{ bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = distMap(name)
    val tw = (length-count).toDouble/count.toDouble
    intval -> tw
  }.sortBy(_._1).map{_._2}.toArray

  lazy val dWeight = new DenseTensor1(weight)

  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  object OutcomeLabelDomain extends CategoricalDomain[String]

  class OutcomeLabel(label : String, val feature : OutcomeFeatures, val name : String = "", val labels : Seq[String], val aid : AidSeq, val doc : Document, val sentence : Sentence) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
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
    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(CombinedSent.featureSize)
  }
  class OutcomeFeatures(st1 : SparseTensor1) extends VectorVariable(st1) {//BinaryFeatureVectorVariable[String] {
  def domain = OutcomeFeaturesDomain
    //override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(aid : AidSeq, pl : Document, labels : Seq[String]) : Seq[OutcomeLabel] =
  {
    val sentences = pl.sentences.toArray
    val length = sentences.length
    sentences.zipWithIndex.map { case (sent, i) =>
      val f = CombinedSent(sent, i.toDouble/length.toDouble, pl.name)//Word2VecSent(sent, i.toDouble/length.toDouble) //Word2Vec(pl)
    val features = new OutcomeFeatures(f) //TfIdf(pl))
      for (l <- labels) {
        new OutcomeLabel(l, features, pl.name, labels, aid, pl, sent)
      }
      new OutcomeLabel(labels.head, features, pl.name, labels, aid, pl, sent)
    }
  }

  def testAccuracy(testData : Seq[OutcomeLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val (eval, f1) = evaluate(testData,classifier)
    println(eval)
    f1
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
    //val classifier = new DecisionTreeMulticlassTrainer(new C45DecisionTreeTrainer).train(trainData, (l : OutcomeLabel) => l.feature, (l : OutcomeLabel) => 1.0)
    //val optimizer = new LBFGS// with L2Regularization //
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(OutcomeLabelDomain.size, OutcomeFeaturesDomain.dimensionSize, (l : OutcomeLabel) => l.feature)/*(objective = new SigmoidalLoss().asInstanceOf[OptimizableObjectives.Multiclass]) {
      override def examples[L<:LabeledDiscreteVar,F<:VectorVar](classifier:LinearVectorClassifier[L,F], labels:Iterable[L], l2f:L=>F, objective:Multiclass): Seq[Example] =
        labels.toSeq.map(l => new PredictorExample(classifier, l2f(l).value, l.target.value, objective))//, weight(l.target.intValue)))
    }*/
    val optimizer = new LBFGS /*with L2Regularization {
     variance = 1000 // LDA
      variance = 1.25 // tfidf
    }*/
    //val trainer = new BatchTrainer(classifier.parameters, optimizer)
    val trainer = new OnlineTrainer(classifier.parameters, optimizer = rda, maxIterations = 3)
    val trainExamples = trainData.map{ td =>
      new PredictorExample(classifier, td.feature.value, td.multiLabel, new WeightedHingeLoss(dWeight), if(td.multiLabel.sum == 1.0) 1.0 else 1.0)
    }
    val shuffed = Random.shuffle(trainExamples)

    while(!trainer.isConverged)
      trainer.processExamples(shuffed)
    //val classifier = trainer.train(trainData, l2f)
    println("Train Acc: ")
    testAccuracy(trainData, classifier)
    println("Test Acc: ")
    (classifier, testAccuracy(testData,classifier))
  }

  def aidToFeature(aid : AidSeq) : Seq[OutcomeLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => Seq()
      case Some(d) =>
        aid.outcome match {
          case a : Seq[Outcome] if a.isEmpty => Seq()
          case a: Seq[Outcome] =>
            docToFeature(aid, d._1,a.map(_.Outcome).map{a => a}.distinct)
        }
    }
  }

}
object OutcomeRanker {
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def main(args: Array[String]): Unit = {
    val distribution = AidSeq.load(args.head).toArray.filter(_.outcome.nonEmpty).flatMap(_.outcome.map{ b => b.Outcome}.distinct).groupBy(a => a).map{a => a._1 -> a._2.length}
    val count = AidSeq.load(args.head).toArray.count(_.outcome.nonEmpty)
    val extractor = new OutcomeRanker(distribution, count)

    val data = AidSeq.load(args.head).toArray/*flatMap{ a =>
      extractor.aidToFeature(a)
    }*/

    val trainLength = (data.length.toDouble * 0.8).toInt
    val testLength = data.length - trainLength
    val trainData = data.take(trainLength).flatMap{ extractor.aidToFeature }
    val testData = data.takeRight(testLength).flatMap( extractor.aidToFeature )
    val testDocuments = data.takeRight(testLength).map{ extractor.aidToFeature }

    val (klass, reg) = (0.00005 to 0.005 by 0.00003).map{ e => (extractor.train(trainData,testData,e),e) }.maxBy(_._1._2)
    val (classifier, f1) = klass
    println(f1)
    println(extractor.evaluate(testData, classifier)._1)
    //val classifier = extractor.train(trainData,testData,0.1)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value

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
    println("\t" + extractor.OutcomeLabelDomain.map{_.category}.mkString("\t") + "\t" + "Alone")
    for(i <- extractor.OutcomeLabelDomain) {
      print(i.category + "\t")
      println(extractor.OutcomeLabelDomain.map{j => corrMatrix(i.intValue,j.intValue)}.mkString("\t"))
    }

    topSentences(testDocuments.filter(_.nonEmpty),classifier,extractor.OutcomeLabelDomain.categories)
    def topSentences(testSet : Array[Seq[extractor.OutcomeLabel]], classifier : MulticlassClassifier[Tensor1], domain : Seq[String]) = {
      for(testExample <- testSet) {
        val trueLabels = testExample.head.aid.outcome.map(a => a.Outcome).distinct.mkString(",")
        val sentences = testExample.flatMap { sent =>
          val klass = classifier.classification(sent.feature.value).prediction.toArray.zipWithIndex
          klass.map { k => (k._2, k._1, sent.sentence) }
        }.groupBy(_._1).map{ p => p._1 -> p._2.sortBy(-_._2)}
        sentences.foreach{ sent =>
          sent._2.take(10).filter(_._2 > -0.05
          ).foreach { example =>
            println(testExample.head.aid.index + "\t" + testExample.head.aid.bib.Authors + "\t" + testExample.head.name + "\t" + domain(sent._1) + "\t" + example._2 + "\t" + trueLabels + "\t" + example._3.string)
          }
        }
      }
    }


  }


}