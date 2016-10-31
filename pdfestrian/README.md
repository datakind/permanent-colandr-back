Pdfestrian 0.0.1-SNAPSHOT
==========================

pdfestrian is a conservation-specific metadata extraction tool for the purposes of speeding up systematic maps. It has two functions:

1. Allow for the extraction of full-text from PDF (using PDFBox)
2. Provide a set of suggested metadata from a research document with provenance (a setence).
    
Installation
------------
You can install pdfestrian using maven.

### on ubuntu:
```
$ sudo apt-get install mvn
```

### on os x
install homebrew if you don't have it yet and then call
```
$ brew install maven
```

### for all
Then in the pdfestrian directory you simply call
```
$ mvn package
```

This will download all dependencies including some model (so it will download somewhere around 1gb worth of data)

Usage
------
### Extracting full-text

Run:
```
$ ./bin/extractText.sh
extractText 0.1
Usage: extractText [options]

  -f, --filename <value>  Filename of pdf
  -h, --html              flag, if on will extract html string instead of plain text
```

### Starting metadata http server

There is some configuration for the server:

First is that you need to add glove.6B.50d.txt.gz to the config directory (TODO: figure out some way to publish the word2vec data. This file doesn't seem available anywhere alone)

Second, you need to modify pdfestrian.conf in the conf directory:
```json
{
  "pdfestrian" : {
    "port" : 5000, //Specify the port you want to run
    "auth" : "plaintext", // Specify the type of authentication. The options are "none" or "plaintext"
    "keys" : {
      "colandr": "thepassword" //Specify a map from user to password for authentication
    }
  }
}
```

You can then start the server with
```
$ ./bin/start.sh
```

and stop the server
```
$ ./bin/stop.sh
```

and restart the server:
```
$ ./bin/restart.sh
```

### Calling the server

There are 4 endpoints to the API

The first is simple, and allows for a system to check if the server is still running:

```
hostname:port/isAlive
```

All the other require authentication (if enabled in the config file)
To authenticate, you need to send two headers:

```
user: username
passwd: password
```
So if you had the default setup (as shown above) you would pass:
```
user: colandr
passwd: thepassword
```

### getRecord

get record simply returns a record from a record id:

```
hostname:port/getRecord/$recordid
```
Which returns a json with the following fields:
```
    id, // The record id
    reviewId, // The id of the review of this record
    citationId, // The id of the citation
    filename, // the filename of the uploaded PDF
    content, // The fulltext extracted from the PDF
```

### getLocations

getLocations returns the list of suggested locations the study took place, and the senteces they were extracted from:
 
```
hostname:post/getLocations/$recordid
```

### getMetadata

getMetadata returns the list of extracted metadata the study took place, and the senteces they were extracted from:

```
hostname:port/getMetadata/$recordid/$medataname
```

Right now, the list of metadata names it can take are: ["biome","interv","outcome"]



Both getLocations and getMetadata returns a list whose contents look as follows:

```
    record, // The record id 
    metaData, // name of type of metadata returned (ex. "biome")
    value, // the predicted field for the metadat (ex. "forest" or "grassland")
    sentence, // the text of the sentence the data was extracted from
    sentenceLocation, // The location in the document the sentence was found (an index into the list of sentences in a document)
    confidence // Score between 0-1 how confident the model is about the extraction here
```
