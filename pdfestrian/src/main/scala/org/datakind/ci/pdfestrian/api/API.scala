package org.datakind.ci.pdfestrian.api

import akka.actor.ActorSystem
import colossus.IOSystem
import colossus.core._
import colossus.protocols.http.HttpMethod._
import colossus.protocols.http.UrlParsing._
import colossus.protocols.http._
import colossus.service.Callback.Implicits._
import colossus.service.{Callback, ServiceConfig}
import org.json4s.NoTypeHints
import org.json4s.jackson.Serialization
import org.json4s.jackson.Serialization.{read, write}
import org.slf4j.LoggerFactory
import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.Future
import org.json4s._
import org.json4s.jackson.JsonMethods._

/**
  * Created by sam on 10/15/16.
  */
trait APIService {
  this: LocationExtraction with MetadataExtraction with FileRetriever with AuthorizationComponent =>
  val logger = LoggerFactory.getLogger(this.getClass)

  implicit val formats = Serialization.formats(NoTypeHints)

  val port : Int
  val headers = HttpHeaders(HttpHeader(HttpHeaders.ContentType, "application/json; charset=utf-8"))


  def getLocationsFuture(record : String) = Future {
    getLocations(record).toString()
  }

  def getMetaDataFuture(record : String, metaData : String) = Future {
    getMetaData(record, metaData).toString()
  }

  class APIService(context : ServerContext) extends HttpService(ServiceConfig.Default, context) {

    def handle = {
      case request@Get on Root / "isAlive" => {
        request.ok(""" {"status":"okay"} """)
      }
      case request@Get on Root / "getRecord" / r => {
        val app = request.head.headers.firstValue("user").getOrElse("")
        val key = request.head.headers.firstValue("passwd").getOrElse("")
        authorize(app, key) match {
          case false =>
            logger.info("Unauthorized\t+" + app + "\t" + key)
            request.unauthorized(s"""{"error":"Unauthorized"}""", headers = headers)
          case true =>
            getFile(r) match {
              case None =>
                logger.info("Requested nonexistant record: " + r)
                request.error(""" {"error":"nonexistant record"}""")
              case Some(result) =>
                request.ok( new HttpBody(write(result).getBytes("UTF-8")), headers = headers)
            }
        }
      }
      case request@Get on Root / "getLocations" => {
        val record  = request.head.parameters.getFirst("record")
        val app = request.head.headers.firstValue("user").getOrElse("")
        val key = request.head.headers.firstValue("passwd").getOrElse("")
        authorize(app, key) match {
          case false =>
            logger.info("Unauthorized\t+" + app + "\t" + key)
            request.unauthorized(s"""{"error":"Unauthorized"}""", headers = headers)
          case true =>
            record match {
              case None => request.error(""" {"error":"Empty Request"} """, headers = headers)
              case Some(r) =>
                Callback.fromFuture(
                  getLocationsFuture(r).map{ result =>
                    request.ok(new HttpBody(result.getBytes("UTF-8")), headers = headers)
                  }
                )
            }
        }
      }
      case request@Get on Root / "getMetadata" => {
        val record  = request.head.parameters.getFirst("record")
        val metaData = request.head.parameters.getFirst("metadata")
        val app = request.head.headers.firstValue("user").getOrElse("")
        val key = request.head.headers.firstValue("passwd").getOrElse("")
        authorize(app, key) match {
          case false =>
            logger.info("Unauthorized\t+" + app + "\t" + key)
            request.unauthorized(s"""{"error":"Unauthorized"}""", headers = headers)
          case true =>
            (record, metaData) match {
              case (None, None) => request.error(""" {"error":"Empty Request"} """, headers = headers)
              case (Some(r), None) => request.error(""" {"error":"No metadata requested"} """, headers = headers)
              case (None, Some(m)) => request.error(""" {"error":"No record requested"} """, headers = headers)
              case (Some(r), Some(m)) =>
                Callback.fromFuture(
                  getMetaDataFuture(r,m).map{ result =>
                    request.ok(new HttpBody(result.getBytes("UTF-8")), headers = headers)
                  }
                )
            }
        }
      }

    }

  }

  def start(port : Int)(implicit system : IOSystem) : ServerRef = {
    Server.start("http-example", port) { implicit worker => new Initializer(worker) {
      def onConnect = context => new APIService(context)
    }}
  }

  def main(args: Array[String]): Unit = {
    implicit val actorSystem = ActorSystem("COLOSSUS")
    implicit val iOSystem = IOSystem()
    start(port)(iOSystem)
  }

}

object API extends APIService
  with LocationExtraction
  with FileRetriever
  with MetadataExtraction
  with AuthorizationComponent {

  val locationExtractor = new DummyLocationExtractor
  val metaDataExtractor = new DummyMetadataExtractor
  val auth = new NoAuth
  val port = 8080
  val access = new DBFileExtractor
}

case class Locations(country : String, confidence : Double)
trait LocationExtraction {
  val locationExtractor : LocationExtractor
  def getLocations(record : String) = locationExtractor.getLocations(record)
}
trait LocationExtractor {
  def getLocations(record : String) : Seq[Locations]
}


case class Metadata(record : String, metaData : String, value : String, sentence : String, sentenceLocation : Int, confidence : Double)


trait MetadataExtraction {
  val metaDataExtractor : MetadataExtractor
  def getMetaData(record : String, metaData : String) : Seq[Metadata] = metaDataExtractor.getMetaData(record, metaData)
}
trait MetadataExtractor {
  def getMetaData(record : String, metaData : String) : Seq[Metadata]
}


trait AuthorizationComponent {
  val auth : Authorization
  def authorize(user : String, passwd : String) : Boolean = auth.authorize(user, passwd)
}

trait Authorization {
  def authorize(user : String, passwd : String) : Boolean
}


class NoAuth extends Authorization {
  def authorize(user: String, passwd: String): Boolean = true
}

trait FileRetriever {
  val access : Access
  def getFile(record : String) : Option[Record] = access.getFile(record)
}

trait Access {
  def getFile(record : String) : Option[Record]
}