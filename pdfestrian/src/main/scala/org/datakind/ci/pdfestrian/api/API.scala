package org.datakind.ci.pdfestrian.api

import com.typesafe.config.ConfigFactory
import configs.Configs
import org.datakind.ci.pdfestrian.extraction.MetadataClassifier

object API extends APIService
  with LocationExtraction
  with FileRetriever
  with MetadataExtraction
  with AuthorizationComponent {

  val config = ConfigFactory.load("pdfestrian.conf")

  val keyMap = Configs[Map[String,String]].get(config, "pdfestrian.keys").valueOrElse(Map())
  val locationExtractor = new org.datakind.ci.pdfestrian.extraction.LocationExtraction("/locationModel")
  val metaDataExtractor = new MetadataClassifier
  val auth = getAuth(Configs[String].get(config, "pdfestrian.auth").valueOrElse(""))
  val port = Configs[Int].get(config, "pdfestrian.port").valueOrElse(8080)
  val access = new DBFileExtractor
}