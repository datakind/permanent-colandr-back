package org.datakind.ci.pdfestrian.api

/**
  * Authorization component to be mixed in to [[APIService]], two types:
  * NoAuth allows for anybody to access service, and PlainText matches password to
  * to userrnames plaintext password.
  */
trait AuthorizationComponent {
  val auth : Authorization
  val keyMap : Map[String, String]

  def authorize(user : String, passwd : String) : Boolean = auth.authorize(user, passwd)

  trait Authorization {
    def authorize(user : String, passwd : String) : Boolean
  }

  class NoAuth extends Authorization {
    def authorize(user : String, passwd : String) : Boolean = true
  }

  class PlaintextAuthorization extends Authorization {
    def authorize(user: String, passwd: String): Boolean = {
      keyMap.get(user) match {
        case None => false
        case Some(key) => passwd == key
      }
    }
  }

  def getAuth(authType : String) : Authorization = {
    authType match {
      case "plaintext" => new PlaintextAuthorization
      case _ => new NoAuth
    }
  }
}