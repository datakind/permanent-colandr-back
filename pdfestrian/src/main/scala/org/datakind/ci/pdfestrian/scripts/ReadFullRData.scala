package org.datakind.ci.pdfestrian.scripts

import java.io.{BufferedWriter, FileWriter}

import com.fasterxml.jackson.databind.ObjectMapper
import com.fasterxml.jackson.module.scala.DefaultScalaModule
import com.fasterxml.jackson.module.scala.experimental.ScalaObjectMapper
import com.github.tototoshi.csv.CSVReader
import org.datakind.ci.pdfestrian.{AllFieldsRecord, BiblioItem, PDFExtractedDataMore}

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

case class Aid(index : Int, pdf : PDFExtractedDataMore, bib : BiblioItem, allFields : AllFieldsRecord, biome : Option[Biome],
               interv : Option[Interv], outcome: Option[Outcome], outcomeHWB : Option[OutcomeHWB], pathway : Option[Pathways],
               study : Option[Study]) extends JsonWriter

object ReadBiome {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("biome.json"))
    val reader = CSVReader.open(args.head).iterator.drop(1)
    val biomes = reader.map{ s =>
      new Biome(s(1).toInt, s(2))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    biomes.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }

  def load(file : String) : Seq[Biome] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Biome])
    }.toSeq
  }
}

object ReadInterv {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("interv.json"))
    val reader = CSVReader.open(args.head).iterator.drop(1)
    val intervs = reader.map{ s =>
      new Interv(s(1).toInt, s(2), s(3), s(4), s(5), s(6), s(7), s(8))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    intervs.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }
  def load(file : String) : Seq[Interv] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Interv])
    }.toSeq
  }
}

object ReadOutcome {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("outcome.json"))
    val reader = CSVReader.open(args.head).iterator.drop(1)
    val outcomes = reader.map{ s =>
      new Outcome(s(1).toInt, s(2).toInt, s(3), s(4), s(5))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    outcomes.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }

  def load(file : String) : Seq[Outcome] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Outcome])
    }.toSeq
  }
}

object ReadOutcomeWB {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("outcomewb.json"))
    val reader = CSVReader.open(args.head).iterator.drop(1)
    val outcomes = reader.map{ s =>
      new OutcomeHWB(s(1).toInt, s(2), s(3), s(4), s(5), s(6).toInt, s(7).toInt, s(8), s(9))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    outcomes.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }
  def load(file : String) : Seq[OutcomeHWB] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[OutcomeHWB])
    }.toSeq
  }
}

object ReadPathways {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("pathways.json"))
    val reader = CSVReader.open(args.head).iterator.drop(1)
    val outcomes = reader.map{ s =>
      new Pathways(s(1).toInt, s(2), s(3), s(4), s(5), s(6), s(7), s(8), s(9), s(10), s(11), s(12), s(13),
        s(14), s(15))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    outcomes.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }
  def load(file : String) : Seq[Pathways] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Pathways])
    }.toSeq
  }
}

object ReadStudy {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("study.json"))
    val reader = CSVReader.open(args.head, "ISO-8859-1").iterator.drop(1)
    val outcomes = reader.map{ s =>
      new Study(s(1).toInt, s(2).toInt, s(3).toInt, s(4).toInt, s(5), s(6), s(7), s(8),
        s(9), s(10), s(11), s(12), s(13), s(14), s(15), s(16), s(17), s(18), s(19), s(20),
        s(21), s(22), s(23))
    }.toSeq.groupBy(_.aid).map{ _._2.head }.toSeq
    outcomes.sortBy(_.aid).foreach( b => out.write(b.toJson + "\n"))
    out.flush()
  }

  def load(file : String) : Seq[Study] = {
    Source.fromFile(file).getLines().map { line =>
      val mapper = new ObjectMapper() with ScalaObjectMapper
      mapper.registerModule(DefaultScalaModule)
      mapper.readValue(line, classOf[Study])
    }.toSeq
  }

}

import org.datakind.ci.pdfestrian.Triple

object AidWriter {
  def main(args: Array[String]) {
    val out = new BufferedWriter(new FileWriter("aid.json"))
    val triples = Triple.load(args.head)
    val biome = ReadBiome.load(args(1)).map{ t => t.aid -> t}.toMap
    val intervs = ReadInterv.load(args(2)).map{ t => t.aid -> t}.toMap
    val outcomes = ReadOutcome.load(args(3)).map{ t => t.aid -> t}.toMap
    val outcomeHWBs = ReadOutcomeWB.load(args(4)).map{ t => t.aid -> t}.toMap
    val pathways = ReadPathways.load(args(5)).map{ t => t.aid -> t}.toMap
    val studys = ReadStudy.load(args(6)).map{ t => t.aid -> t}.toMap
    val allAids = triples.map{ t =>
      val aid = t.bib.aid
      Aid(index = aid, pdf = t.pdf, bib = t.bib, allFields = t.allFields,
        biome = biome.get(aid), interv = intervs.get(aid), outcome = outcomes.get(aid),
        outcomeHWB = outcomeHWBs.get(aid), pathway = pathways.get(aid), study = studys.get(aid)
      )
    }
    allAids.sortBy(_.index).foreach{ aid =>
      out.write(aid.toJson + "\n")
    }
    out.flush()
  }
}