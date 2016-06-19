package org.datakind.ci.pdfestrian.extraction

import java.io.{BufferedWriter, File, FileWriter}

import cc.factorie.app.nlp.Document

import scala.collection.mutable
import scala.io.Source

/**
  * Created by sameyeam on 6/18/16.
  */
object FindTopWords {
  val stopWords = Source.fromInputStream(getClass.getResourceAsStream("/stopwords.txt")).getLines().toSet
  def getDocuments(file : File) : Seq[Document]= {
    for(f <- file.listFiles(); if f.getAbsolutePath.endsWith("txt")) yield
      PDFToDocument.fromFile(f)
  }

  val counters = new mutable.HashMap[String, Int]() {
    override def default(string : String) : Int = {
      this(string) = 0
      0
    }
  }

  def main(args: Array[String]) {
    val allDocs = args.flatMap{a =>
      getDocuments(new File(a))
    }
    for(doc <- allDocs; token <- doc.asSection.tokens; if (token.string.length > 2 || (token.string.length > 1 && !token.string.endsWith("."))) && !token.isDigits && !token.isPunctuation && !stopWords.contains(token.string.toLowerCase())) {
      val tokenString = token.string.toLowerCase()
      counters(tokenString) = counters(tokenString) + 1
    }
    val out = new BufferedWriter(new FileWriter("goodWords.txt"))
    counters.toSeq.filter(_._2 > 30).sortBy(-_._2).foreach( w => out.write(w + "\n"))
    out.flush()
  }
}
