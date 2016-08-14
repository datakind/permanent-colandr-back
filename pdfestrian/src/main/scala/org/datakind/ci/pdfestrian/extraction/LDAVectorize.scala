package org.datakind.ci.pdfestrian.extraction

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.Document

import scala.io.Source

/**
  * Created by sam on 8/14/16.
  */
object LDAVectorize {

    val ldavectors = Source.fromInputStream(getClass.getResourceAsStream("/docs50-topic.txt")).getLines().map{ l =>
      val split = l.split("\t")
      val tensor = split.takeRight(50).map{_.toDouble}
      val filename = split(1).split("/").last.dropRight(8).replaceAll("%20"," ")
      filename -> new DenseTensor1(tensor)
    }.toMap
    val featureSize = 50


    def apply(name : String) : DenseTensor1 = {
      if(ldavectors.contains(name)) ldavectors(name) else new DenseTensor1(featureSize)
    }

  }
