package org.datakind.ci.pdfestrian.extraction.features

import java.util.zip.GZIPInputStream

import scala.collection.mutable
import scala.io.Source

case class Word(word : String, vector : Array[Float])
case class Vectors(words : Map[String, Word], dim : Int)

/**
  * Mapper to hold vectors in memory so as to prevent many classes using the vectors to reload them.
  * usage:  W2VVectors(key) where key is the vectors in memory, initially it will load them
  * from a resource in classpath "/$key" and later on it will use a cached version.
  */
object W2VVectors {
  private val vectorMap = new mutable.HashMap[String, Vectors] {
    override def default(key : String) : Vectors = {
      val vectorMap = Source.fromInputStream(new GZIPInputStream(getClass.getResourceAsStream("/" + key))).getLines().map { word =>
        val split = word.split(" ")
        split.head -> Word(split.head, split.tail.map{_.toFloat})
      }.toMap
      val vectors = Vectors(vectorMap, vectorMap.head._2.vector.length)
      this(key) = vectors
      vectors
    }
  }

  def apply(vectorLoc : String) = vectorMap(vectorLoc)
}
