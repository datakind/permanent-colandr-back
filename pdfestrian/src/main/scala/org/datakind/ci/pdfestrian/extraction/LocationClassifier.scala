package org.datakind.ci.pdfestrian.extraction


import java.io._

import cc.factorie.Factorie.CategoricalVectorDomain
import cc.factorie.app.classify.{LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, OptimizingLinearVectorClassifierTrainer, Serialize}
import cc.factorie.app.nlp.{Document, Token}
import cc.factorie.util.BinarySerializer
import cc.factorie.variable._
import org.datakind.ci.pdfestrian.api.{LocationExtractor, Metadata, Record}
import org.datakind.ci.pdfestrian.scripts.Aid

import scala.io.Source
import scala.util.Random

object LocationClassifier {

  implicit val rand = new Random()

  val countries = Source.fromInputStream(getClass.getResourceAsStream("/countries.txt")).getLines().toSeq
      .map{_.toLowerCase}.toSet

  object LocationLabelDomain extends CategoricalDomain[String]  {
    this += "false"
    this += "true"
    this.freeze()
  }

  class LocationLabel(label : String, val feature : LocationFeatures) extends CategoricalVariable[String](label) with CategoricalLabeling[String] {
    def domain = LocationLabelDomain
  }

  object LocationFeaturesDomain extends CategoricalVectorDomain[String]
  class LocationFeatures() extends BinaryFeatureVectorVariable[String] {
    def domain = LocationFeaturesDomain
    override def skipNonCategories = true
  }

  def clean(string : String) : String = {
    val lower = string.toLowerCase()
    lower.filter(_.isLetterOrDigit)
  }

  def sentenceToFeature(pl : PredictedLocation) : LocationLabel = {
    val features = new LocationFeatures()
    for(words <- pl.sentences.flatMap(p => p.sentence.split(" ").map{clean})) {
      if(countries.contains(words))
        features += "COUNTRY"
      features += words
    }
    features += "LENGTH=" + (pl.sentences.length * 2) % 10
    for(sentence <- pl.sentences) {
      val location = (sentence.percent * 10.0).floor.toInt
      features += "LOC=" + location
    }
    new LocationLabel(pl.valid.toString, features)
  }

  def trainDataToFeatures(locationTrainData: LocationTrainData) : Seq[LocationLabel] = {
     locationTrainData.sentences.map{ sentenceToFeature }
  }

  def testAccuracy(testData : Seq[LocationLabel], classifier : cc.factorie.app.classify.LinearVectorClassifier[LocationLabel, LocationFeatures]) : Double = {
      val correct = testData.count{ td => classifier.bestLabelIndex(td) == td.target.intValue}
      correct.toDouble/testData.length
  }

  def l2f(l : LocationLabel) = l.feature

  def train(trainData : Seq[LocationLabel], testData : Seq[LocationLabel]) :
        cc.factorie.app.classify.LinearVectorClassifier[LocationLabel, LocationFeatures] = {
    val trainer = new OnlineOptimizingLinearVectorClassifierTrainer()
    val classifier = trainer.train(trainData, l2f)
    println("Train Acc: " + testAccuracy(trainData,classifier) )
    println("Test Acc: " + testAccuracy(testData,classifier) )
    import cc.factorie.util.CubbieConversions._
    val is = new DataOutputStream(new BufferedOutputStream(new FileOutputStream("locationModel")))
    BinarySerializer.serialize(LocationFeaturesDomain, is)
    BinarySerializer.serialize(classifier, is)
    is.flush()
    is.close()
    classifier
  }


  def train(fullData : Seq[LocationLabel]) : cc.factorie.app.classify.LinearVectorClassifier[LocationLabel, LocationFeatures] = {
    val trainSize = (fullData.length.toDouble * 0.8).toInt
    val testSize = fullData.length - trainSize
    val shuf = Random.shuffle(fullData)
    val trainData = shuf.take(trainSize)
    val testData = shuf.takeRight(testSize)
    train(trainData, testData)
  }

  def main(args: Array[String]): Unit = {
    val saveTo = args.last
    val trainData = LocationTrainData.fromFile(args.head).filter( _.sentences.exists(_.valid))
    println("Training with: " + trainData.length)
    val labels = trainData.flatMap(trainDataToFeatures)
    val model = train(labels)
    val os = new DataOutputStream(new BufferedOutputStream(new FileOutputStream(saveTo)))
    BinarySerializer.serialize(LocationFeaturesDomain, os)
    BinarySerializer.serialize(model, os)
    os.flush()
    os.close()
  }

}


class LocationExtraction(modelLoc : String) extends LocationExtractor {
  import LocationClassifier._
  val model : cc.factorie.app.classify.LinearVectorClassifier[LocationLabel, LocationFeatures] = {
    val is = new DataInputStream(new BufferedInputStream(getClass.getResourceAsStream(modelLoc)))
    BinarySerializer.deserialize(LocationFeaturesDomain, is)
    LocationFeaturesDomain.freeze()
    val classifier = new cc.factorie.app.classify.LinearVectorClassifier[LocationLabel, LocationFeatures](2,LocationFeaturesDomain.dimensionSize,l2f)
    BinarySerializer.deserialize(classifier, is)
    classifier
  }

  def getLocations(record: Record): Seq[Metadata] = {
    val labels = GetAllLocations.featureData(record.content).get.sentences.map{ i => (i,sentenceToFeature(i))}
    val classification = labels.map{ l =>
      val prob = model.classification(l._2.feature.value).proportions(1)
      l -> prob
    }
    classification.sortBy(-_._2).take(5).map{c =>
      Metadata(record.id.toString, "location", c._1._1.location, c._1._1.sentences.map{_.sentence}.mkString("\n"), 0, c._2)
    }
  }

}

object LocationExtraction {
  val extractor = new LocationExtraction("/locationModel")

  def main(args: Array[String]): Unit = {
    val doc = Source.fromFile(args.head)
    println(extractor.getLocations(Record(1,1,1,args.head,doc.getLines().mkString(""))))
  }
}