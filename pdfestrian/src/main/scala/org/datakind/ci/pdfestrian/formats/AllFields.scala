package org.datakind.ci.pdfestrian.formats

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

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