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
import org.json4s.NoTypeHints
import org.json4s.jackson.Serialization
import org.json4s.jackson.Serialization.write
import org.slf4j.LoggerFactory

import scala.concurrent.ExecutionContext.Implicits.global
import scala.concurrent.Future


/**
  * API service that needs to be implemented to launch server.
  * Created with simple scala dependency injection, object to launch server needs to have
  * mixed-in all traits defined after "with".
  */
trait APIService {
  this: LocationExtraction
    with AllMetaDataExtraction
    with FileRetriever
    with AuthorizationComponent =>

  val logger = LoggerFactory.getLogger(this.getClass)

  implicit val formats = Serialization.formats(NoTypeHints)

  val port: Int
  val headers = HttpHeaders(HttpHeader(HttpHeaders.ContentType, "application/json; charset=utf-8"))

  def logAndWrite(record : Record, f : Record => Seq[Metadata]) : String = {
    val start = System.currentTimeMillis()
    val results = f(record)
    val time = System.currentTimeMillis() - start
    val labels = results.map{_.metaData}.distinct.mkString(",")
    logger.info(s"Got record request for metadata for record ${record.id} with labels returned: \t $labels in $time ms")
    write(results)
  }

  def getLocationsFuture(record: Record) = Future {
    logAndWrite(record, record => getLocations(record))
  }

  def getAllMetaDataFuture(record: Record) = Future {
    logAndWrite(record, record => extractData(record))
  }

  def getAllMetaDataFuture(record: Record, meta : String) = Future {
    logAndWrite(record, record => extractData(record).filter(_.metaData == meta))
  }


  class APIService(context: ServerContext) extends HttpService(ServiceConfig.Default, context) {

    def withAuthorization(request: http.Http#Input)(f: (http.Http#Input => Callback[http.Http#Output])): Callback[http.Http#Output] = {
      val app = request.head.headers.firstValue("user").getOrElse("")
      val key = request.head.headers.firstValue("passwd").getOrElse("")
      authorize(app, key) match {
        case false =>
          logger.info(s"Unauthorized\t$app\tkey")
          request.unauthorized(body("""{"error":"Unauthorized"}"""), headers = headers)
        case true =>
          f(request)
      }
    }

    def body(string : String) : HttpBody = {
      new HttpBody(string.getBytes("UTF-8"))
    }

    def withRecord(request: http.Http#Input, r: String)(f: (Record => Future[String])): Callback[http.Http#Output] = {
      getFile(r) match {
        case None =>
          logger.info("Requested nonexistant record: " + r)
          request.error(body(""" {"error":"nonexistant record"}"""), headers = headers)
        case Some(record) if record.content == null => request.error(s""" {"error":"Record $r does not have fulltext attached"} """, headers = headers)
        case Some(record) =>
          Callback.fromFuture(
            f(record).map { result =>
              request.ok(body(result), headers = headers)
            }
          )
      }
    }

    def handle = {
      case request@Get on Root / "isAlive" => {
        request.ok(body(""" {"status":"okay"} """), headers = headers)
      }

      case request@Get on Root / "getRecord" / r => {
        withAuthorization(request) { request =>
          withRecord(request, r) { record =>
            logger.info(s"Got record request for record $r with result reviewId\t${record.reviewId}\trecordId\t${record.id}\tfilename\t${record.filename}")
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
            getAllMetaDataFuture(record, meta)
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
    }}
  }

  def main(args: Array[String]): Unit = {
    implicit val actorSystem = ActorSystem("COLOSSUS")
    implicit val iOSystem = IOSystem()
    start(port)(iOSystem)
  }

}