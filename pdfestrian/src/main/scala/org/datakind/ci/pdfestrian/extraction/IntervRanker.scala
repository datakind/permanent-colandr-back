package org.datakind.ci.pdfestrian.extraction

import java.io._

import cc.factorie.{DenseTensor1, DenseTensor2}
import cc.factorie.app.classify.backend.{LinearMulticlassClassifier, _}
import cc.factorie.app.classify.{Classification => _, _}
import cc.factorie.app.nlp.{Document, Sentence}
import cc.factorie.app.strings.PorterStemmer
import cc.factorie.la._
import cc.factorie.model.{DotTemplateWithStatistics2, Parameters}
import cc.factorie.optimize.OptimizableObjectives.Multiclass
import cc.factorie.optimize._
import cc.factorie.util.{BinarySerializer, DoubleAccumulator}
import cc.factorie.variable._
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.api.{Metadata, Record}
import org.datakind.ci.pdfestrian.scripts.{Aid, AidSeq, Interv}

import scala.collection.mutable
import scala.collection.mutable.ArrayBuffer
import scala.io.Source
import scala.reflect.ClassTag
import scala.util.Random

/**
  * Created by sameyeam on 8/1/16.
  */
class IntervRanker(distMap : Map[String,Int], length : Int) {

  lazy val weight = IntervLabelDomain.map{ bio =>
    val name = bio.category
    val intval = bio.intValue
    val count = distMap(name)
    val tw = (length-count).toDouble/count.toDouble
    intval -> tw
  }.sortBy(_._1).map{_._2}.toArray

  lazy val dWeight = new DenseTensor1(weight)

  implicit val rand = new Random()
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().map{ _.toLowerCase}.toSet

  object IntervLabelDomain extends CategoricalDomain[String]

  class IntervLabel(label : String, val feature : IntervFeatures, val name : String = "", val labels : Seq[String], val aid : Option[AidSeq], val doc : Document, val sentence : Sentence) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = IntervLabelDomain
    def multiLabel : DenseTensor1 = {
      val dt = new DenseTensor1(IntervLabelDomain.size)
      for(l <- labels) {
        dt(IntervLabelDomain.index(l)) = 1.0
      }
      dt
    }
  }

  object IntervFeaturesDomain extends VectorDomain {
    override type Value = SparseTensor1
    override def dimensionDomain: DiscreteDomain = new DiscreteDomain(CombinedSent.featureSize)
  }
  class IntervFeatures(st1 : SparseTensor1) extends VectorVariable(st1) {//BinaryFeatureVectorVariable[String] {
  def domain = IntervFeaturesDomain
    //override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def docToFeature(aid : Option[AidSeq], pl : Document, labels : Seq[String]) : Seq[IntervLabel] =
  {
    val sentences = pl.sentences.toArray.filter(_.length > 70)
    val length = sentences.length
    sentences.zipWithIndex.map { case (sent, i) =>
      val f = CombinedSent(sent, i.toDouble/length.toDouble, pl.name)//Word2VecSent(sent, i.toDouble/length.toDouble) //Word2Vec(pl)
    val features = new IntervFeatures(f) //TfIdf(pl))
      for (l <- labels) {
        new IntervLabel(l, features, pl.name, labels, aid, pl, sent)
      }
      new IntervLabel(labels.headOption.getOrElse(""), features, pl.name, labels, aid, pl, sent)
    }
  }

  def testAccuracy(testData : Seq[IntervLabel], classifier : MulticlassClassifier[Tensor1]) : Double = {
    val (eval, f1) = evaluate(testData,classifier)
    println(eval)
    f1
  }

  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }


  def evaluate(testData : Seq[IntervLabel], classifier : MulticlassClassifier[Tensor1]) : (String,Double) = {
    val trueCounts = new Array[Int](IntervLabelDomain.size)
    val correctCounts = new Array[Int](IntervLabelDomain.size)
    val predictedCounts = new Array[Int](IntervLabelDomain.size)

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
    val each = IntervLabelDomain.indices.map{ i =>
      val brec = if(predictedCounts(i) == 0) 0.0 else correctCounts(i).toDouble/predictedCounts(i).toDouble * 100.0
      val bec = if(trueCounts(i) == 0) 0.0 else correctCounts(i).toDouble/trueCounts(i).toDouble * 100.0
      val bf1 = if(bec + bec == 0) 0.0 else (2.0 * brec * bec) / (brec + bec)
      f"${IntervLabelDomain(i).category}\t$brec%2.2f\t$bec%2.2f\t$bf1%2.2f\t${correctCounts(i)}\t${predictedCounts(i)}\t${trueCounts(i)}"
    }.mkString("\n")
    ("Category:\tPrecision\tRecall\tCorrect\tPredicted\tTrue\n" + total + each, f1)
  }

  def l2f(l : IntervLabel) = l.feature


  def train(trainData : Seq[IntervLabel], testData : Seq[IntervLabel], l2 : Double) :
  (LinearVectorClassifier[IntervLabel, IntervFeatures], Double) = {
    //val classifier = new DecisionTreeMulticlassTrainer(new C45DecisionTreeTrainer).train(trainData, (l : IntervLabel) => l.feature, (l : IntervLabel) => 1.0)
    //val optimizer = new LBFGS// with L2Regularization //
    val rda = new AdaGradRDA(l1 = l2)
    val classifier = new LinearVectorClassifier(IntervLabelDomain.size, IntervFeaturesDomain.dimensionSize, (l : IntervLabel) => l.feature)/*(objective = new SigmoidalLoss().asInstanceOf[OptimizableObjectives.Multiclass]) {
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

  def aidToFeature(aid : AidSeq) : Seq[IntervLabel] = {
    PDFToDocument.apply(aid.pdf.filename) match {
      case None => Seq()
      case Some(d) =>
        aid.interv match {
          case a : Seq[Interv] if a.isEmpty => Seq()
          case a: Seq[Interv] =>
            docToFeature(Some(aid), d._1,a.map(_.Int_type).map{a => IntervMap(a)}.distinct)
        }
    }
  }

}
object IntervRanker {
  def sigmoid(d : Double) : Double = {
    1.0/(1.0f + math.exp(-d))
  }

  def main(args: Array[String]): Unit = {
    val distribution = AidSeq.load(args.head).toArray.filter(_.interv.nonEmpty).flatMap(_.interv.map{ b => IntervMap(b.Int_type)}.distinct).groupBy(a => a).map{a => a._1 -> a._2.length}
    val count = AidSeq.load(args.head).toArray.count(_.interv.nonEmpty)
    val extractor = new IntervRanker(distribution, count)

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
    val dos = new DataOutputStream(new BufferedOutputStream(new FileOutputStream("intervExtractorModel")))
    BinarySerializer.serialize(extractor.IntervLabelDomain, dos)
    BinarySerializer.serialize(classifier, dos)
    dos.flush()
    dos.close()

    println(f1)
    println(extractor.evaluate(testData, classifier)._1)
    //val classifier = extractor.train(trainData,testData,0.1)
    val weights = classifier.asInstanceOf[LinearVectorClassifier[_,_]].weights.value

    val matrix = new DenseTensor2(extractor.IntervLabelDomain.length, extractor.IntervLabelDomain.length)
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

    println("\t" + extractor.IntervLabelDomain.map{_.category}.mkString("\t"))
    for(i <- extractor.IntervLabelDomain) {
      print(i.category + "\t")
      println(extractor.IntervLabelDomain.map{j => matrix(i.intValue,j.intValue)}.mkString("\t"))
    }
    val corrMatrix = new DenseTensor2(extractor.IntervLabelDomain.length, extractor.IntervLabelDomain.length)
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
    println("\t" + extractor.IntervLabelDomain.map{_.category}.mkString("\t") + "\t" + "Alone")
    for(i <- extractor.IntervLabelDomain) {
      print(i.category + "\t")
      println(extractor.IntervLabelDomain.map{j => corrMatrix(i.intValue,j.intValue)}.mkString("\t"))
    }

    topSentences(testDocuments.filter(_.nonEmpty),classifier,extractor.IntervLabelDomain.categories)
    def topSentences(testSet : Array[Seq[extractor.IntervLabel]], classifier : MulticlassClassifier[Tensor1], domain : Seq[String]) = {
      for(testExample <- testSet) {
        val trueLabels = testExample.head.aid.get.interv.map(a => IntervMap(a.Int_type)).distinct.mkString(",")
        val sentences = testExample.flatMap { sent =>
          val klass = classifier.classification(sent.feature.value).prediction.toArray.zipWithIndex
          klass.map { k => (k._2, k._1, sent.sentence) }
        }.groupBy(_._1).map{ p => p._1 -> p._2.sortBy(-_._2)}
        sentences.foreach{ sent =>
          sent._2.take(10).filter(_._2 > -0.05
          ).foreach { example =>
            println(testExample.head.aid.get.index + "\t" + testExample.head.aid.get.bib.Authors + "\t" + testExample.head.name + "\t" + domain(sent._1) + "\t" + example._2 + "\t" + trueLabels + "\t" + example._3.string)
          }
        }
      }
    }


  }


}

class IntervClassifier(val modelLoc : String) {
  val dis = new DataInputStream(new BufferedInputStream(new FileInputStream(modelLoc)))
  val extractor = new IntervRanker(Map[String, Int](),0)
  BinarySerializer.deserialize(extractor.IntervLabelDomain, dis)
  val model = new LinearVectorClassifier[extractor.IntervLabel, extractor.IntervFeatures](extractor.IntervLabelDomain.dimensionSize,extractor.IntervFeaturesDomain.dimensionSize, (l : extractor.IntervLabel) => l.feature)
  BinarySerializer.deserialize(model, dis)
  val domain = extractor.IntervLabelDomain.categories
  def extract(record : Record) : Seq[Metadata] = {
    val (d, _) = PDFToDocument.fromString(record.content,record.filename)
    val labels = extractor.docToFeature(None,d,Seq())
    labels.flatMap{ l =>
      model.classification(l.feature.value).prediction.toArray
        .zipWithIndex.map{ p => (p._2, p._1, l.sentence) }
        .filter(_._2 > -0.05).map{ p =>
        Metadata(record.id.toString,"intervention", domain(p._1),l.sentence.tokensString(" "),l.sentence.indexInSection,p._2)
      }
    }
  }
}

object IntervClassifier {
  def main(args: Array[String]): Unit = {
    val doc = Source.fromFile(args.head)
    val record = Record(1,1,1,args.head,doc.getLines().mkString(""))
    val outcome = new OutcomeClassifier("intervExtractorModel")
    println(outcome.extract(record))
  }
}