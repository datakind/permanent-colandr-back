package org.datakind.ci.pdfestrian.api

import akka.actor.ActorSystem
import colossus.IOSystem
import colossus.core._
import colossus.protocols.http
import colossus.protocols.http.HttpMethod._
import colossus.protocols.http.UrlParsing._
import colossus.protocols.http._
import colossus.service.Callback.Implicits._
import colossus.service.{Callback, ServiceConfig}
import org.datakind.ci.pdfestrian.extraction.ReviewTrainer
import org.json4s.NoTypeHints
import org.json4s.jackson.Serialization
import org.json4s.jackson.Serialization.write
import org.slf4j.LoggerFactory

import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.Future

/**
  * Created by sam on 10/15/16.
  */
trait APIService {
  this: LocationExtraction with MetadataExtraction with FileRetriever with AuthorizationComponent =>
  val logger = LoggerFactory.getLogger(this.getClass)

  implicit val formats = Serialization.formats(NoTypeHints)

  val port: Int
  val headers = HttpHeaders(HttpHeader(HttpHeaders.ContentType, "application/json; charset=utf-8"))


  def getLocationsFuture(record: Record) = Future {
    write(getLocations(record))
  }

  def getMetaDataFuture(record: Record, metaData: String) = Future {
    write(getMetaData(record, metaData))
  }

  def getAllMetaDataFuture(record: Record) = Future {
    ReviewTrainer.getModel(record.reviewId) match {
      case None => "[]"
      case Some(model) => model.classifier match {
        case None => "[]"
        case Some(m) => write(m.getMetaData(record))
      }
    }
  }

  class APIService(context: ServerContext) extends HttpService(ServiceConfig.Default, context) {


    def withAuthorization(request: http.Http#Input)(f: (http.Http#Input => Callback[http.Http#Output])): Callback[http.Http#Output] = {
      val app = request.head.headers.firstValue("user").getOrElse("")
      val key = request.head.headers.firstValue("passwd").getOrElse("")
      authorize(app, key) match {
        case false =>
          logger.info("Unauthorized\t+" + app + "\t" + key)
          request.unauthorized(s"""{"error":"Unauthorized"}""", headers = headers)
        case true =>
          f(request)
      }
    }

    def withRecord(request: http.Http#Input, r: String)(f: (Record => Future[String])): Callback[http.Http#Output] = {
      getFile(r) match {
        case None =>
          logger.info("Requested nonexistant record: " + r)
          request.error(""" {"error":"nonexistant record"}""")
        case Some(record) if record.content == null => request.error(s""" {"error":"Record $r does not have fulltext attached"} """, headers = headers)
        case Some(record) =>
          Callback.fromFuture(
            f(record).map { result =>
              request.ok(new HttpBody(result.getBytes("UTF-8")), headers = headers)
            }
          )
      }
    }

    def handle = {
      case request@Get on Root / "isAlive" => {
        request.ok(""" {"status":"okay"} """)
      }

      case request@Get on Root / "getRecord" / r => {
        withAuthorization(request) { request =>
          withRecord(request, r) { record =>
            Future(write(record))
          }
        }
      }

      case request@Get on Root / "getLocations" / r => {
        withAuthorization(request) { request =>
          withRecord(request, r) { record =>
            getLocationsFuture(record)
          }
        }
      }

      case request@Get on Root / "getMetadata" / r / meta => {
        withAuthorization(request) { request =>
          withRecord(request, r) { record =>
            getMetaDataFuture(record, meta)
          }
        }
      }

      case request@Get on Root / "getMetadata" / r => {
        withAuthorization(request) { request =>
          withRecord(request, r) { record =>
            getAllMetaDataFuture(record)
          }
        }
      }

    }
  }

  def start(port: Int)(implicit system: IOSystem): ServerRef = {
    Server.start("http-example", port) { implicit worker => new Initializer(worker) {
      def onConnect = context => new APIService(context)
    }
    }
  }

  def main(args: Array[String]): Unit = {
    implicit val actorSystem = ActorSystem("COLOSSUS")
    implicit val iOSystem = IOSystem()
    start(port)(iOSystem)
  }

}