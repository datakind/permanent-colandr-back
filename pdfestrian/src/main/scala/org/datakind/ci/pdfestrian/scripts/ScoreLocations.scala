package org.datakind.ci.pdfestrian.scripts

import java.io.File

import scala.io.Source

/**
  * Created by sameyeam on 7/18/16.
  */
object ScoreLocations {

  case class Location(title : String, location : String, predicted : Array[String]) {
    override def toString : String = {
       title + "\n" +
        location + "\n" +
         predicted.mkString("; ") + "\n"
    }
  }

  def getIterator(file : File) : Iterator[Location] = new Iterator[Location] {
    val source = Source.fromFile(file).getLines().drop(2)

    def hasNext() = source.nonEmpty

    def next() : Location = {
      val plines = source.takeWhile(_ != "======================").toArray
      val lines = if(plines.length == 4) plines.drop(1) else plines
      if(lines.length == 3) {
        val title = lines.head
        val location = if (lines(1) == "Viet Nam") "vietnam"
        else if (lines(1).startsWith("Tanzania")) "tanzania"
        else if (lines(1).startsWith("Iran")) "iran"
        else if( lines(1).startsWith("Taiwan")) "taiwan"
        else lines(1)
        val predicted = lines(2).split(", ").map {
          _.toLowerCase
        }.groupBy(a => a).map { a => a._1 -> a._2.length }
          .toArray.sortBy(-_._2).map {
          _._1
        }
        source.take(2)
        Location(title, location, predicted)
      } else {
        source.take(2)
        Location(lines.head, "", Array())
      }
    }
  }

  def score(file : File) : Double = {
    var count = 0
    var found = 0
    getIterator(file).foreach{ l =>
      if(l.location.trim.length > 0 && l.location != "NA") {
        count += 1
        val search = l.location.toLowerCase()
        if (l.predicted.contains(search))
          found += 1
        else {
          println(l)
          println()
        }
      }
    }
    found.toDouble / count
  }

  def main(args: Array[String]) {
    val recall = score(new File(args.head))
    println("Recall: " + recall)
  }

}
