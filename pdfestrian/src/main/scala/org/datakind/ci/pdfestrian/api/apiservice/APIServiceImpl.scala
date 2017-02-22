package org.datakind.ci.pdfestrian.api.apiservice

import org.datakind.ci.pdfestrian.api.apiservice.components.{AllMetaDataExtraction, AuthorizationComponent, FileRetriever, LocationExtraction}

trait APIServiceImpl extends APIService
with LocationExtraction
with FileRetriever
with AllMetaDataExtraction
with AuthorizationComponent
