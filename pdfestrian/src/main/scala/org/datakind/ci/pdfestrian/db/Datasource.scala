package org.datakind.ci.pdfestrian.db

import java.net.URI
import java.sql.Connection

import org.apache.commons.dbcp2.BasicDataSource

object Datasource {
  lazy val connectionPool = {
    val cp = new BasicDataSource()

    val dbUri = new URI(System.getenv("COLANDR_DATABASE_URI"))
    val dbUrl = s"jdbc:postgresql://${dbUri.getHost}:${dbUri.getPort}${dbUri.getPath}"
    if (dbUri.getUserInfo != null) {
      cp.setUsername(dbUri.getUserInfo.split(":")(0))
      cp.setPassword(dbUri.getUserInfo.split(":")(1))
    }
    cp.setDriverClassName("org.postgresql.Driver")
    cp.setUrl(dbUrl)
    cp.setInitialSize(3)
    cp
  }

  def getConnection : Connection = connectionPool.getConnection
}
