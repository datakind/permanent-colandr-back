package org.datakind.ci.pdfestrian.api.apiservice.components

import org.datakind.ci.pdfestrian.api.apiservice.Record

/**
  * Trait to be mixed in to APIservice to implement access to a record
  */
trait FileRetriever {
  val access : Access

  /**
    * Gets a record from an id
    * @param record record id
    * @return Option, record returned if id exists, None otherwise
    */
  def getFile(record : String) : Option[Record] = access.getFile(record)
}

/**
  * Trait to implement record access
  */
trait Access {
  /**
    * Gets a record from an id
    * @param record record id
    * @return Option, record returned if id exists, None otherwise
    */
  def getFile(record : String) : Option[Record]
}