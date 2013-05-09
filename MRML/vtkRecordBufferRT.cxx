
#include "vtkRecordBufferRT.h"

vtkStandardNewMacro( vtkRecordBufferRT );

vtkRecordBufferRT
::vtkRecordBufferRT()
{
  this->numRecords = 0;
  this->recordSize = 0;
}


vtkRecordBufferRT
::~vtkRecordBufferRT()
{
  records.clear();
}


vtkLabelRecord* vtkRecordBufferRT
::GetRecordRT()
{
  return GetRecordAt( numRecords - 1 );
}


void vtkRecordBufferRT
::SetRecordRT( vtkLabelRecord* newRecord )
{
  return SetRecord( numRecords - 1, newRecord );
}


vtkLabelVector* vtkRecordBufferRT
::DistancesRT( std::vector<ValueRecord> valueRecords )
{
  // Create a new order record
  vtkLabelVector* distRecord;
  distRecord.initialize( valueRecords.size(), 0.0 );

  double currSum;

  for ( int j = 0; j < valueRecords.size(); j++ )
  {
      
    // First, ensure that the records are the same size
    if ( this->recordSize != valueRecords[j].size() )
    {
      return distRecord;
    }

    // Initialize the sum to zero
    currSum = 0.0;

    for ( int d = 0; d < recordSize; d++ )
    {
      currSum = currSum + ( this->GetRecordRT().get(d) - valueRecords[j].get(d) ) * ( this->GetRecordRT().get(d) - valueRecords[j].get(d) );
	}
	// Add to the current order record
	distRecord.set( j, currSum );
  }

  // Add the current order record to the vector
  distRecord.setLabel( 0 );

  return distRecord;

}


vtkLabelRecord* vtkRecordBufferRT
::DerivativeRT( int order )
{
  // To calculate a derivative of arbitrary order, we need arbitrarily many time stamps
  // Just calculate zeroth order first order derivative here, otherwise use other method
  if ( numRecords < 2 )
  {
    vtkLabelRecord* derivRecord;

    for( int d = 0; d < recordSize; d++ )
    {
      derivRecord.add( 0.0 );
    }
	
    derivRecord.setTime( GetRecordAt(numRecords-1).getTime() );
    derivRecord.setLabel( GetRecordAt(numRecords-1).getLabel() );
    
	return derivRecord;
  }

  if ( order == 0 )
  {
    return GetRecordRT();
  }

  if ( order == 1 )
  {
    double DT = GetRecordAt(numRecords-1).getTime() - GetRecordAt(numRecords-2).getTime();
    vtkLabelRecord* derivRecord;

    for( int d = 0; d < recordSize; d++ )
    {
      derivRecord.add( ( GetRecordAt(numRecords-1).get(d) - GetRecordAt(numRecords-2).get(d) ) / DT );
    }
	
    derivRecord.setTime( GetRecordAt(numRecords-1).getTime() );
    derivRecord.setLabel( GetRecordAt(numRecords-1).getLabel() );
    
	return derivRecord;
  }

  vtkRecordLog* derivRecordLog = Derivative( order );
  return derivRecordLog->GetRecordAt( derivRecordLog->Size() - 1 );

}



vtkLabelRecord* vtkRecordBufferRT
::GaussianFilterRT( double width )
{
  // Create a new record valuestor
  vtkLabelRecord* gaussRecord;
  gaussRecord.initialize( recordSize, 0.0 );

  // Iterate over all dimensions
  for ( int d = 0; d < recordSize; d++ )
  {
    double weightSum = 0;
    double normSum = 0;
	double gaussWeight;
	double normDist;

    // Iterate over all records nearby
	int j = numRecords - 1;
	while ( j >= 0 ) // Iterate backward
    {
	  // If too far from "peak" of distribution, the stop - we're just wasting time
	  normDist = ( GetRecordAt(j).getTime() - GetRecordRT().getTime() ) / width;
	  if ( abs( normDist ) > STDEV_CUTOFF )
	  {
	    break;
	  }

      // Calculate the values of the Gaussian distribution at this time
	  gaussWeight = exp( - normDist * normDist / 2 );
	  // Add the product with the values to function sum
      weightSum = weightSum + GetRecordAt(j).get(d) * gaussWeight;
	  // Add the values to normSum
	  normSum = normSum + gaussWeight;

	  j--;
    }

    // Add to the new values
    gaussRecord.set( d, weightSum / normSum );

  }

  // Add the new record vector to the record log
  gaussRecord.setTime( GetRecordRT().getTime() );
  gaussRecord.setLabel( GetRecordRT().getLabel() );

  return gaussRecord;
}



vtkLabelRecord* vtkRecordBufferRT
::OrthogonalTransformationRT( int window, int order )
{
  // Pad the recordlog with values at the beginning (only if necessary)
  vtkRecordLog* padRecordLog;
  vtkRecordLog* padCatRecordLog;
  if ( numRecords <= window )
  {
    padRecordLog = this->PadStart( window );
	padCatRecordLog = padRecordLog->Concatenate( this );
  }
  else
  {
    padRecordLog = NULL;
    padCatRecordLog = this;
  }

  // Calculate the record log to include
  vtkRecordLog* trimRecordLog = padCatRecordLog->Trim( padCatRecordLog->Size() - 1 - window, padCatRecordLog->Size() - 1 );
	
  // Create a new matrix to which the Legendre coefficients will be assigned
  std::vector<vtkLabelVector*> legCoeffMatrix = trimRecordLog->LegendreTransformation( order );
  
  vtkLabelRecord* legRecord;
  legRecord.initialize( this->recordSize * ( order + 1 ), 0.0 );

  // Calculate the Legendre coefficients: 2D -> 1D
  int count = 0;
  for ( int o = 0; o <= order; o++ )
  {
    for ( int d = 0; d < recordSize; d++ )
    {
      legRecord.set( count, legCoeffMatrix[o].get(d) );
	  count++;
    }
  }

  // New value record to add to the record log
  legRecord.setTime( GetRecordRT().getTime() );
  legRecord.setLabel( GetRecordRT().getLabel() );


  if ( numRecords <= window )
  {
    padRecordLog->Delete();
	padCatRecordLog->Delete();
  }
  trimRecordLog->Delete();

  return legRecord;

}


vtkLabelRecord* vtkRecordBufferRT
::TransformPCART( std::vector<vtkLabelVector*> prinComps, ValueRecord mean )
{
  // Create a vtkLabelRecord* for the transformed record log
  vtkLabelRecord* transRecord;
  transRecord.initialize( prinComps.size(), 0.0 );

  // Initialize the components of the transformed time record to be zero
  for ( int o = 0; o < prinComps.size(); o++ )
  {	  
    // Iterate over all dimensions, and perform the transformation (ie vector multiplcation)
    for ( int d = 0; d < recordSize; d++ )
	{
      transRecord.set( o, transRecord.get(o) + ( GetRecordRT().get(d) - mean.get(d) ) * prinComps[o].get(d) );
	}
  }

  // Add the time record to the new transformed record log
  transRecord.setTime( GetRecordRT().getTime() );
  transRecord.setLabel( GetRecordRT().getLabel() );

  return transRecord;

}



vtkLabelRecord* vtkRecordBufferRT
::fwdkmeansTransformRT( std::vector<vtkLabelVector*> centroids )
{
  // Calculate closest cluster centroid to last
  // Find the record farthest from any centroid
  // Tricky way to cast vector of vtkLabelVector* to vector of ValeuRecord
  vtkLabelVector* centDist = this->DistancesRT( std::vector<ValueRecord>( centroids.begin(), centroids.end() ) );

  double currMinDist = centDist.get(0);
  int currMinCentroid = 0;
  // Minimum for each point
  for ( int c = 0; c < centroids.size(); c++ )
  {
    if ( centDist.get(c) < currMinDist )
	{
      currMinDist = centDist.get(c);
	  currMinCentroid = c;
	}
  }

  vtkLabelRecord* clustRecord;
  clustRecord.add( currMinCentroid );
  clustRecord.setTime( GetRecordRT().getTime() );
  clustRecord.setLabel( GetRecordRT().getLabel() );
  
  return clustRecord;

}


MarkovRecord vtkRecordBufferRT
::ToMarkovRecordRT()
{
  MarkovRecord markovRecord;

  // We will assume that: label -> state, values[0] -> symbol
  markovRecord.setState( this->GetRecordRT().getLabel() );
  markovRecord.setSymbol( this->GetRecordRT().get(0) );

  return markovRecord;

}