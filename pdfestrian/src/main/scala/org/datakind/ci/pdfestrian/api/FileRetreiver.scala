package org.datakind.ci.pdfestrian.api

trait FileRetriever {
  val access : Access
  def getFile(record : String) : Option[Record] = access.getFile(record)
}

trait Access {
  def getFile(record : String) : Option[Record]
}