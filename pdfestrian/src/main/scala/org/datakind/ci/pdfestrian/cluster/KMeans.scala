package org.datakind.ci.pdfestrian.cluster

import java.io.{BufferedWriter, FileWriter}

import cc.factorie.DenseTensor1
import cc.factorie.app.nlp.Document
import cc.factorie.la.{DenseTensor, DenseTensor1, SparseTensor1}
import org.datakind.ci.pdfestrian.extraction.{PDFToDocument, TfIdf}
import org.datakind.ci.pdfestrian.scripts.{Aid, Biome}

import scala.collection.mutable.ArrayBuffer
import scala.util.Random

/**
  * Created by sameyeam on 8/6/16.
  */
class KMeans(val K : Int, dim : Int) {
  val rand = new Random
  val clusters = Array.fill(K)(new DenseTensor1(dim))// (0 until dim).map{a => math.abs(rand.nextDouble())}.toArray))
  val counts = Array.fill(K)(1)


  def initialize(all : Seq[SparseTensor1]) : Unit = {
    var current = 1
    clusters(0) = new DenseTensor1(all(rand.nextInt(all.length)).toArray)
    while (current < K) {
      val next = all.map { st =>
        val d = new DenseTensor1(st.toArray)
        (0 until current).map{ i => clusters(i).euclideanDistance(d) }.min
      }.zipWithIndex.maxBy(_._1)._2
      clusters(current) = new DenseTensor1(all(next).toArray)
      current += 1
    }
    /*for(k <- clusters) {
      println(k.mkString(","))
    }*/
  }

  def +=(st : SparseTensor1) : Int = {
    val d = new DenseTensor1(st.toArray)
    val cluster = clusters.map{ _.euclideanDistance(d)}.zipWithIndex.minBy(_._1)._2
    val currentProb = counts(cluster).toDouble/(counts(cluster).toDouble + 1)
    val nextProb = 1.0/(counts(cluster).toDouble + 1)
    counts(cluster) += 1
    clusters(cluster) = ((clusters(cluster) * currentProb) + (d * nextProb)).asInstanceOf[DenseTensor1]
    cluster
  }

  def predict(st : SparseTensor1) : (Int, Double) = {
    val d = new DenseTensor1(st.toArray)
    clusters.map{ _.euclideanDistance(d)}.zipWithIndex.minBy(_._1).swap
  }
}

object KMeans {

  def getDocument(a : Aid) : Option[(Aid,Document,SparseTensor1)] = {
    PDFToDocument(a.pdf.filename) match {
      case Some((d,d2)) =>
        Some((a,d,TfIdf(d)))
      case None =>
        None
    }
  }
  var iter = 10
  def main(args: Array[String]): Unit = {
    val data = Aid.load(args.head).flatMap { a =>
      getDocument(a)
    }
    val K = args.last.toInt
    val clusterer = new KMeans(K, TfIdf.featureSize)

    clusterer.initialize(data.map{_._3})
    for(i <- 0 until iter; d <- data) {
      clusterer += d._3
    }
    val clusters = Array.fill(K)(new ArrayBuffer[(String,String)]())
    for(d <- data) {
      val cluster = clusterer.predict(d._3)._1
      val point = (d._1.pdf.filename, d._1.biome.getOrElse(Biome(0,"")).biome)
      clusters(cluster) += point
    }
    for((c,i) <- clusters.zipWithIndex) {
      val out = new BufferedWriter(new FileWriter(s"cluster$i.txt"))
      out.write(c.map{ a => a._1 + "\t" + a._2}.mkString("\n"))
      out.flush()
      out.close()
    }
  }
}
