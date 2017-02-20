package org.datakind.ci.pdfestrian.scripts

import java.sql.ResultSet

import org.datakind.ci.pdfestrian.db.Datasource
import org.datakind.ci.pdfestrian.formats.AidSeq

import scala.collection.mutable.ListBuffer
import scala.io.Source

case class Citation(id : Int, title : String, authors : String, issn : String, doi : String)

class DBCitationFinder {
  def getCitation(title: String): Option[Citation] = {
    val cx = Datasource.getConnection
    val query = cx.prepareStatement("select id, title, authors, issn, doi from citations as c where c.title = ?")
    try {
      query.setString(1, title)
      toRecord(query.executeQuery())
    } finally {
      query.close()
      cx.close()
    }
  }

  def toRecord(results : ResultSet) : Option[Citation] = {
    getItems(results, results => Citation(results.getInt(1), results.getString(2), results.getString(3), results.getString(4), results.getString(5))).toArray.headOption
  }

  def getItems[E](results : ResultSet, getItem : ResultSet => E) : Traversable[E] = {
    val items = new ListBuffer[E]
    while(results.next())
      items += getItem(results)
    items
  }
}

class FindDBIDs {
  val finder = new DBCitationFinder
  def getIds(aids : Seq[AidSeq]) : Map[Int, Int] = {
    val map = aids.flatMap{ aid =>
       val title = aid.allFields.Title
       val citation = finder.getCitation(title)
       citation match {
         case Some(cit) => Some(aid.index -> cit.id)
         case None => None
       }
    }.toMap
    val aidLength = aids.length
    val mapSize = map.size
    println(s"Found $mapSize out of $aidLength citations")
    map
  }
}

object FindDBIDs {
  def main(args: Array[String]): Unit = {
    val finder = new FindDBIDs
    val aids = AidSeq.load(args.head)
    println(finder.getIds(aids).map{ case (a,b) => s"$a\t$b"}.mkString("\n"))
  }
}