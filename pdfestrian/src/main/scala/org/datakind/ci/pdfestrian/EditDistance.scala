package org.datakind.ci.pdfestrian

import com.sun.corba.se.spi.orb.StringPair
import scala.collection.mutable

/**
  * Computes the edit distance between pairs of words.  Can be used for applications
  * like finding near-match names in Kevin Bacon or spelling correction.
  *
  * There are two versions: a recursive version and a dynamic programming version
  * that memoizes the function by storing previously solved problems in a map.
  *
  * @author Scot Drysdale
  */
class EditDistance {
  var solvedProblems = mutable.HashMap[StringPair, Integer]()

  /**
    * Computes the edit distance between two strings.  The valid operations are:
    *   1) Insert a character
    *   2) Delete a character
    *   3) Replace a character
    *   4) Twiddle (Swap two characters to match the output).
    *
    * This version is memoized to avoid re-solving problems.
    *
    * @param s1 The source string
    * @param s2 The destination string
    * @return the number of edit operations to turn s1 into s2
    */
  def memoizedEditDist(s1 : String, s2 : String) : Int = {
    solvedProblems = new mutable.HashMap[StringPair, Integer]()

    editDist(s1, s2)
  }


  /**
    * A helper function for memoizedEditDistance that uses a Map
    * to keep track of problems that have already been solved.
    *
    * @param s1 The source string
    * @param s2 The destination string
    * @return the number of edit operations to turn s1 into s2
    */
  def editDist(s1 : String, s2 : String) : Int =  {
    var matchDist = 0;   // Edit distance if first char. match or do a replace
    var insertDist = 0;  // Edit distance if insert first char of s1 in front of s2.
    var deleteDist = 0 ;  // Edit distance if delete first char of s2.
    var swapDist = 0;    // edit distance for twiddle (first 2 char. must swap).

    if(s1.length() == 0)
      s2.length();   // Insert the remainder of s2
    else  if (s2.length()== 0)
      s1.length();   // Delete the remainder of s1
    else {
      val pair =new  StringPair(s1, s2)
      val result = solvedProblems.get(pair)

      if(result.isDefined)  // Did we find the subproblem in the map?
         result.get;    // If so, return the answer
      else {
        matchDist = editDist(s1.substring(1), s2.substring(1))
        if(s1.charAt(0) != s2.charAt(0))
          matchDist += 1;  // If first 2 char. don't match must replace

        insertDist = editDist(s1.substring(1), s2) + 1
        deleteDist = editDist(s1, s2.substring(1)) + 1

        if(s1.length() > 1 && s2.length() > 1 &&
          s1.charAt(0) == s2.charAt(1) && s1.charAt(1) == s2.charAt(0))
          swapDist = editDist(s1.substring(2), s2.substring(2)) + 1
        else
          swapDist = Integer.MAX_VALUE;  // Can't swap if first 2 char. don't match

        val dist = Math.min(matchDist, Math.min(insertDist, Math.min(deleteDist, swapDist)))

        solvedProblems.put(pair, dist)  // Save the result for future

        dist
      }
    }
  }

  /**
    * Testing program
    */
}

object EditDistance {

  def apply(s1 : String, s2 : String) : Int = {
    new EditDistance().memoizedEditDist(s1,s2)
  }

}

