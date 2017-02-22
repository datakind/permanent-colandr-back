package org.datakind.ci.pdfestrian.formats

import java.io.File

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper

import scala.io.Source

/**
  * Created by sanzaroot on 6/12/16.
  */
trait JsonWriter {
  def toJson : String = {
    val mapper = new ObjectMapper() with ScalaObjectMapper
    mapper.registerModule(DefaultScalaModule)
    mapper.writeValueAsString(this)
  }
}

case class Biome(aid : Int, biome : String) extends JsonWriter
case class Interv(aid : Int , Int_area : String, Int_geo : String, Int_dur : String, Int_type : String,
                  Impl_type : String, Desired_outcome : String, Int_notes : String) extends JsonWriter
case class Outcome(aid : Int, Equity : Int, Equity_cat : String, Outcome : String, Outcome_notes : String) extends JsonWriter
case class OutcomeHWB(aid : Int, OutcomeHWB_gen_cat : String, OutcomeHWB_spec_cat : String,
        OutcomeHWB_groups : String, OutcomeHWB_Data_type : String,
        OutcomeHWB_Percept : Int, OutcomeHWB_Equity : Int, OutcomeHWB : String, OutcomeHWB_impact : String)  extends JsonWriter
case class Pathways(aid : Int, Expl_mechanism : String, Concept_mod : String, Concept_mod_name : String,
                    Factors : String, Factor_type : String, ES : String, ES_mechanism : String, Part_sys_rev : String,
                    Sys_rev_name : String, Summary : String, ES_type : String, ES_subtype : String, Disservices : String,
                    Pathway_notes : String) extends JsonWriter
case class Study(aid : Int, Study_obj_env : Int, Study_obj_soc : Int, Study_obj_econ : Int,
                 HWB : String, Sample_size : String, Indep_eval : String, Study_scale : String,
                 Study_country : String, Comps : String, Comps_type : String, Comps_time : String,
                 Design_qual_only : String, Design_assigned : String, Design_control : String,
                 Sex_disagg : String, Marg_groups : String, Eval_affil_type : String, Marg_cat : String,
                 Data_source : String, Data_type : String, Study_location : String, Study_notes : String) extends JsonWriter

case class AidSeq(index : Int, pdf : PDFExtractedData, bib : BiblioItem, allFields : AllFieldsRecord, biome : Seq[Biome],
                  interv : Seq[Interv], outcome: Seq[Outcome], outcomeHWB : Seq[OutcomeHWB], pathway : Seq[Pathways],
                  study : Seq[Study]) extends JsonWriter


object AidSeq {
  val mapper = new ObjectMapper() with ScalaObjectMapper
  mapper.registerModule(DefaultScalaModule)
  def load(string : String) : Seq[AidSeq] = {
    val source = Source.fromFile(new File(string))
    source.getLines().map{ l =>
      mapper.readValue[AidSeq](l)
    }.toSeq
  }
}