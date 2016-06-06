package org.datakind.ci.pdfestrian

import java.io.{BufferedWriter, FileWriter}

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.collection.mutable
import scala.io.Source

/**
  * Created by samanzaroot on 6/5/16.
  */
case class AllFieldsRecord(Title : String = "", Record_Number : String = "", Short_Title : String = "",
                           Notes : String = "", URL : String = "", Reference_Type : String = "", Author : String = "",
                           Abstract : String = "", Year : String = "", Author_Address : String = "", Pages : String = "",
                           Volume : String = "", Journal : String = "", Issue : String = "", Keywords : String = "",
                           Source : String = "", Export_Date : String = "", Cited_Reference_Count : String = "",
                           Language : String = "", Accession_Number : String = "", Times_Cited : String = "",
                           Cited_References : String = "", Type_of_Article : String = "", ISSN : String = "",
                           Alternate_Journal : String = "", DOI : String = "", Date : String = "", Series_Title : String = "",
                           Publisher : String = "", Place_Published : String = "", ISBN : String = "", Number_of_Pages : String = "",
                           Series_Editor : String = "", Art_No : String = "", Book_Title : String = "", Year_of_Conference : String = "",
                           Editor : String = "", Article_Number : String = "", Abbreviation : String = "", Series_Volume : String = "",
                           Edition : String = "")
  {
    def toJson : String = {
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.writeValueAsString(this)
    }
  }
class AllFields {

  val keys = Set("Title", "Record Number", "Short Title", "Notes", "URL", "Reference Type", "Author", "Abstract", "Year", "Author Address",
    "Pages", "Volume", "Journal", "Issue", "Keywords", "Source", "Export Date", "Cited Reference Count", "Language", "Accession Number",
    "Times Cited", "Cited References", "Type of Article", "ISSN", "Alternate Journal", "DOI", "Date", "Series Title", "Publisher",
    "Place Published", "ISBN", "Number of Pages", "Series Editor", "Art. No.", "Book Title", "Year of Conference", "Editor",
    "Article Number", "Abbreviation", "Series Volume", "Edition")

  def parseRecord(string : String) : AllFieldsRecord = {
    val kvs = string.split("\n").flatMap{ s =>
      if(!s.startsWith(" ") && s.contains(": ") && keys.contains(s.split(": ").head)) {
        val split = s.split(": ",2)
        Some(split.head -> split.last)
      } else None
    }.toMap
    AllFieldsRecord(Title = kvs.getOrElse("Title",""), Record_Number = kvs.getOrElse("Record Number",""), Short_Title = kvs.getOrElse("Short Title",""),
      Notes = kvs.getOrElse("Notes",""), URL = kvs.getOrElse("URL",""), Reference_Type = kvs.getOrElse("Reference Type", ""), Author = kvs.getOrElse("Author", ""),
      Abstract = kvs.getOrElse("Abstract",""), Year = kvs.getOrElse("Year", ""), Author_Address = kvs.getOrElse("Author Address",""),
      Pages = kvs.getOrElse("Pages",""), Volume = kvs.getOrElse("Volume",""), Journal = kvs.getOrElse("Journal",""), Issue = kvs.getOrElse("Issue",""),
      Keywords = kvs.getOrElse("Keywords",""), Source = kvs.getOrElse("Source",""), Export_Date = kvs.getOrElse("Export Date",""),
      Cited_Reference_Count = kvs.getOrElse("Cited Reference Count",""), Language = kvs.getOrElse("Language",""),
      Accession_Number = kvs.getOrElse("Accession Number",""),  Times_Cited = kvs.getOrElse("Times Cited",""),
      Cited_References = kvs.getOrElse("Cited References",""), Type_of_Article = kvs.getOrElse("Type of Article",""),
      ISSN = kvs.getOrElse("ISSN",""), Alternate_Journal = kvs.getOrElse("Alternate_Journal",""), DOI = kvs.getOrElse("DOI",""),
      Date = kvs.getOrElse("Date",""), Series_Title = kvs.getOrElse("Series_Title",""), Publisher = kvs.getOrElse("Series_Title",""),
      Place_Published = kvs.getOrElse("Place Published",""), ISBN = kvs.getOrElse("ISBN",""), Number_of_Pages = kvs.getOrElse("Number of Pages",""),
      Series_Editor = kvs.getOrElse("Series Editor",""), Art_No = kvs.getOrElse("Art. No.",""), Book_Title = kvs.getOrElse("Book Title",""),
      Year_of_Conference = kvs.getOrElse("Year of Conference",""), Editor = kvs.getOrElse("Editor",""),
      Article_Number = kvs.getOrElse("Article Number",""), Abbreviation = kvs.getOrElse("Abbreviation",""),
      Series_Volume = kvs.getOrElse("Series Volume",""), Edition = kvs.getOrElse("Edition",""))
  }

  val sb = new mutable.StringBuilder()

  def save(dir : String, ref : AllFieldsRecord): Unit = {
    val out = new BufferedWriter(new FileWriter("dir/"+ref.Record_Number + ".json"))
    out.write(ref.toJson + "\n")
    out.flush()
    out.close()
  }

  def parse(string : String) : Unit = {
    if(string.trim.length==0 && sb.nonEmpty) {
      val reference = parseRecord(sb.mkString)
      sb.clear()
      save("all",reference)
    } else {
      sb.append(string + "\n")
    }
  }

}

object AllFields {
  def main(args: Array[String]) {
    val af = new AllFields
    Source.fromFile(args.head).getLines().foreach{ af.parse }
  }
}