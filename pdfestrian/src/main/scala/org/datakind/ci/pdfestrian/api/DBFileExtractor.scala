package org.datakind.ci.pdfestrian.api

import java.net.URI
import java.sql.{Connection, ResultSet}

import scala.collection.mutable.ListBuffer
import org.apache.commons.dbcp2._

object Datasource {
  lazy val connectionPool = {
    val cp = new BasicDataSource()

    val dbUri = new URI(System.getenv("COLANDR_DATABASE_URI"))
    val dbUrl = s"jdbc:postgresql://${dbUri.getHost}:${dbUri.getPort}${dbUri.getPath}"
    if (dbUri.getUserInfo != null) {
      cp.setUsername(dbUri.getUserInfo.split(":")(0))
      cp.setPassword(dbUri.getUserInfo.split(":")(1))
    }
    cp.setDriverClassName("org.postgresql.Driver")
    cp.setUrl(dbUrl)
    cp.setInitialSize(3)
    cp
  }

  def getConnection : Connection = connectionPool.getConnection
}

case class Record(id : Int, reviewId : Int, citationId : Int, filename : String, content : String)

class DBFileExtractor extends Access {
  override def getFile(record: String): Option[Record] = {
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select f.id, f.review_id, f.filename, f.text_content from fulltexts as f where f.id = ?")
    try {
      query.setInt(1, record.toInt)
      toRecord(query.executeQuery())
    } finally {
      query.close()
      cx.close()
    }
  }

  def toRecord(results : ResultSet) : Option[Record] = {
    getItems(results, results => Record(results.getInt(1), results.getInt(2), results.getInt(1), results.getString(3), results.getString(4))).toArray.headOption
  }

  def getItems[E](results : ResultSet, getItem : ResultSet => E) : Traversable[E] = {
    val items = new ListBuffer[E]
    while(results.next())
      items += getItem(results)
    items
  }
}
