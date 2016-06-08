package org.datakind.ci.pdfestrian

import java.io.{File, FileInputStream}

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.collection.mutable
import scala.io.Source

/**
  * Created by samanzaroot on 6/5/16.
  */
class SimpleSearchEngine[A] {
  val map = new mutable.HashMap[String,Set[A]]()

  def load(string : String, elem : A) : Unit = {
    GrobidAccuracy.clean(string).split(" ").foreach { e =>
      map.get(e) match {
        case None =>
          map(e) = Set(elem)
        case Some(a) =>
          map(e) = map(e) ++ Set(elem)
      }
    }
  }

  def load(seq : Seq[(String, A)]) : Unit = seq.foreach(a => load(a._1, a._2))

  def search(string : String) : Seq[A] = {
    GrobidAccuracy.clean(string).split(" ").flatMap { e =>
      map.get(e) match {
        case None => Nil
        case Some(els) => els.toSeq
      }
    }.groupBy( a => a).map{ e => e._1 -> e._2.length}.toSeq.sortBy(- _._2).map{_._1}
  }
  def searchWithCounts(string : String) : Seq[(A,Int)] = {
    GrobidAccuracy.clean(string).split(" ").flatMap { e =>
      map.get(e) match {
        case None => Nil
        case Some(els) => els.toSeq
      }
    }.groupBy( a => a).map{ e => e._1 -> e._2.length}.toSeq.sortBy(- _._2)
  }
}

object SimpleSearchEngine {
  def main(args: Array[String]) {
    val combined = CombinedLoader.load(new FileInputStream(args.head))
    val searcher = new SimpleSearchEngine[Combined]
    searcher.load(combined.map { c => (c.title, c) })
    while(true) {
      val read = readLine(">> ")
      println(searcher.searchWithCounts(read).take(5).mkString("\n"))
    }
  }
}

object AllRefsSearchEngline {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)

  def loadFromFile(s : String) : AllFieldsRecord = {
    val source = Source.fromFile("dir/"+s+".json")
    val json = source.getLines().mkString
    source.close()
    mapper.readValue[AllFieldsRecord](json)
  }

  def main(args: Array[String]) {
    val dir = new File("dir").listFiles().filter(_.getAbsolutePath.endsWith("json"))
    val searcher = new SimpleSearchEngine[String]
    dir.foreach{ f =>
      val source = Source.fromFile(f)
      val json = source.getLines().mkString
      source.close()
      searcher.load(mapper.readValue[AllFieldsRecord](json).Title, mapper.readValue[AllFieldsRecord](json).Record_Number)
    }
    while(true) {
      val read = readLine(">> ")
      println(searcher.searchWithCounts(read).map{ a => (loadFromFile(a._1),a._2)}.take(5).mkString("\n"))
    }
  }
}