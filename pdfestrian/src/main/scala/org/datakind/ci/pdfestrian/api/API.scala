package org.datakind.ci.pdfestrian.api

import com.typesafe.config.ConfigFactory
import configs.Configs
import org.datakind.ci.pdfestrian.extraction.MetadataClassifier

object API extends APIService
  with LocationExtraction
  with FileRetriever
  with MetadataExtraction
  with AllMetaDataExtraction
  with AuthorizationComponent {

  val config = ConfigFactory.load("pdfestrian.conf")

  val keyMap = Configs[Map[String,String]].get(config, "pdfestrian.keys").valueOrElse(Map())
  val locationExtractor = new org.datakind.ci.pdfestrian.extraction.LocationExtraction("/locationModel")
  val metaDataExtractor = new MetadataClassifier
  val auth = getAuth(Configs[String].get(config, "pdfestrian.auth").valueOrElse(""))
  val port = Configs[Int].get(config, "pdfestrian.port").valueOrElse(8080)
  val access = new DBFileExtractor
  val minimum: Int = Configs[Int].get(config, "pdfestrian.min_to_train").valueOrElse(40)
  val numMoreDataToRetrain: Int = Configs[Int].get(config, "pdfestrian.increase_to_retrain").valueOrElse(5)
  val allMetaDataExtractor: AllMetaDataExtractor = new ReviewMetadataExtractor
}