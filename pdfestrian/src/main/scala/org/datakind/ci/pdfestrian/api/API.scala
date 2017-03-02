package org.datakind.ci.pdfestrian.api

import com.typesafe.config.ConfigFactory
import configs.Configs
import org.datakind.ci.pdfestrian.api.apiservice.APIServiceImpl
import org.datakind.ci.pdfestrian.api.apiservice.components._
import org.datakind.ci.pdfestrian.db.DBFileExtractor
import org.datakind.ci.pdfestrian.extraction.impl.{GetAllLocations, ReviewMetadataExtractor}
import org.slf4j.LoggerFactory

/**
  * Implements API, reads configuration using typesafe.config and launches service using
  * the information in config file
  */
object API extends APIServiceImpl {
  val config = ConfigFactory.load("pdfestrian.conf")

  val keyMap = Configs[Map[String,String]].get(config, "pdfestrian.keys").valueOrElse(Map())
  val locationExtractor = new GetAllLocations

  val auth = getAuth(Configs[String].get(config, "pdfestrian.auth").valueOrElse(""))
  val port = Configs[Int].get(config, "pdfestrian.port").valueOrElse(8080)
  val access = new DBFileExtractor
  val minimum: Int = Configs[Int].get(config, "pdfestrian.min_to_train").valueOrElse(40)
  val numMoreDataToRetrain: Int = Configs[Int].get(config, "pdfestrian.increase_to_retrain").valueOrElse(5)
  val threshold: Double = Configs[Double].get(config, "pdfestrian.threshold").valueOrElse(0.65)
  val w2vSource: String = Configs[String].get(config, "pdfestrian.w2vSource").valueOrElse("glove.6B.50d.txt.gz")

  val allMetaDataExtractor: AllMetaDataExtractor = new ReviewMetadataExtractor

  logger.info(s"Starting service with threshold: $threshold, min: $minimum, numMore: $numMoreDataToRetrain" +
    s"and w2v source: $w2vSource")

}