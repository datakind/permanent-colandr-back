package org.datakind.ci.pdfestrian.extraction


import cc.factorie.Factorie.CategoricalVectorDomain
import cc.factorie.app.classify.{LinearVectorClassifier, OnlineOptimizingLinearVectorClassifierTrainer, OptimizingLinearVectorClassifierTrainer}
import cc.factorie.app.nlp.{Document, Token}
import cc.factorie.variable._

import scala.io.Source
import scala.util.Random

/**
  * Created by sameyeam on 7/25/16.
  */
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
    val trainData = LocationTrainData.fromFile(args.head).filter( _.sentences.exists(_.valid))
    println("Training with: " + trainData.length)
    val labels = trainData.flatMap(trainDataToFeatures)
    train(labels)
  }

}
