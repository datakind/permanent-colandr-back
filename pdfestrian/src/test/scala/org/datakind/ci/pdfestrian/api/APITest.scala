package org.datakind.ci.pdfestrian.api

import org.datakind.ci.pdfestrian.api.apiservice.{APIServiceImpl, Metadata, Record}
import org.datakind.ci.pdfestrian.api.apiservice.components.{Access, AllMetaDataExtractor, LocationExtractor}
import org.datakind.ci.pdfestrian.db.{MockDB, MockDBExtractor, MockTrainingData}
import org.datakind.ci.pdfestrian.extraction.impl.{GetAllLocations, ReviewMetadataExtractor}
import org.json4s.DefaultFormats
import org.scalatest.{FlatSpec, Matchers}
import org.json4s.jackson.Serialization._

import scalaj.http.Http

/**
  * Created by sameyeam on 2/20/17.
  */
class APITest extends FlatSpec with Matchers {
  implicit val formats = DefaultFormats

  val portnum = 3465
   object TestAPI extends APIServiceImpl {
     override val port: Int = portnum
     override val minimum: Int = 1
     override val numMoreDataToRetrain: Int = 2
     override val threshold: Double = 0.0
     override val allMetaDataExtractor: AllMetaDataExtractor = new ReviewMetadataExtractor
     override val w2vSource: String = "mock2vec.txt.gz"
     override val auth = new NoAuth
     override val keyMap: Map[String, String] = Map()
     override val locationExtractor: LocationExtractor = new GetAllLocations
     override val access: Access = new MockDBExtractor
   }

  TestAPI.main(Array())

  val host = s"http://localhost:$portnum/"

  def getRecord(id : String) : Option[Record] = {
    val response = Http(s"$host/getRecord/$id").asString
    if(response.isError)
      None
    else {
      Some(read[Record](response.body))
    }
  }

  def getMetadata(id : String) : Seq[Metadata] = {
    val response = Http(s"$host/getMetadata/$id").timeout(Int.MaxValue,Int.MaxValue).asString
    if(response.isError)
      Seq()
    else {
      read[Seq[Metadata]](response.body)
    }
  }


  "Get record" should "get a record" in {
    getRecord("0") should be (MockDB("0"))
    getRecord("3") should be (MockDB("3"))
    getRecord("10") should be (MockDB("10"))
  }

  "Get metadata with no training data" should "return nothing" in {
    getMetadata("0") should be (Seq())
  }


  "Get metadata with some training data" should "return something" in {
    MockTrainingData.add()
    MockTrainingData.add()
    getMetadata("0").length should be > 0
  }




}
