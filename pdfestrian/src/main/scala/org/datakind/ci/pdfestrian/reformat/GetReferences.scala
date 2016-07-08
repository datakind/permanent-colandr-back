package org.datakind.ci.pdfestrian.reformat

import java.io.{BufferedWriter, File, FileWriter}

import cc.factorie.app.nlp.{Document, Sentence, Token}
import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper
import org.datakind.ci.pdfestrian.AllFieldsRecord

import scala.io.Source

/**
  * Created by sameyeam on 6/26/16.
  */
object GetReferences {

  def isRefStart(token : Token) : Boolean = {
    if(token.string.toLowerCase == "references") return true
    if(token.string.toLowerCase == "works" && token.hasNext && token.next.string.toLowerCase == "cited") return true
    if(token.string.toLowerCase == "literature" && token.hasNext && token.next.string.toLowerCase == "cited") return true
    false
  }

  def extract(doc : Document) : Document = {
    val regular = doc.asSection.tokens.takeWhile( t => !isRefStart(t)).length
    val referenceTokens = doc.asSection.tokens.drop(regular)
    val document = new Document()
    val sentence = new Sentence(document)
    referenceTokens.map{ t =>
      new Token(sentence, t.string)
    }
    document
  }
}

object GetAuthors {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)

  def main(args: Array[String]) {
    val dir = "/Users/sameyeam/ci/conservation-intl/pdfestrian/dir"
     val out = new BufferedWriter(new FileWriter("authors.txt"))
     new File(dir).listFiles().filter(d => d.getAbsolutePath.endsWith("json")).map { d =>
      val source = Source.fromFile(d)
      val json = source.getLines().mkString
      source.close()
      val authors = mapper.readValue[AllFieldsRecord](json).Author
       val authorText = authors.split("\\s+").map{_.trim}.filter( s => s.length > 1 && s.head.isUpper && s(1) != '.')
         .map{ _.replace(",","") }
       authorText.foreach{ a => out.write(a + "\n")}
    }
    out.flush()
  }
}
