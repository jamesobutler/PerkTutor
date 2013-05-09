
#ifndef __vtkWorkflowToolCollection_h
#define __vtkWorkflowToolCollection_h

// Standard Includes
#include <string>
#include <sstream>
#include <vector>
#include <cmath>

// VTK includes
#include "vtkObject.h"
#include "vtkObjectBase.h"
#include "vtkObjectFactory.h"
#include "vtkXMLDataElement.h"

// Workflow Segmentation includes
#include "vtkSlicerWorkflowSegmentationModuleMRMLExport.h"
#include "vtkWorkflowTool.h"

// This class stores a vector of values and a string label
class VTK_SLICER_WORKFLOWSEGMENTATION_MODULE_MRML_EXPORT 
vtkWorkflowToolCollection : public vtkObject
{
public:
  vtkTypMacro( vtkWorkflowToolCollection, vtkObject );

  // Standard MRML methods
  static vtkWorkflowToolCollection* New();

protected:

  // Constructo/destructor
  vtkWorkflowToolCollection();
  virtual ~vtkWorkflowToolCollection();

private:
  std::vector<vtkWorkflowTool*> tools;
  double maxTime;
  double minTime;

public:

  int GetNumTools();
  vtkWorkflowTool* GetToolAt( int index );
  vtkWorkflowTool* GetToolByName( std::string name );

  bool GetDefined();
  bool GetInputted();
  bool GetTrained();

  // TODO: This timekeeping should take care of itself, and not need to be called explicitly
  double GetMinTime();
  double GetMaxTime();
  double GetTotalTime();

  std::string PerkProcedureToXMLString();
  void PerkProcedureFromXMLElement( vtkXMLDataElement* element );

  std::string InputParameterToXMLString();
  void InputParameterFromXMLElement( vtkXMLDataElement* element );

  std::string TrainingParameterToXMLString();
  void TrainingParameterFromXMLElement( vtkXMLDataElement* element );

  std::string BuffersToXMLString();
  void BuffersFromXMLElement( vtkXMLDataElement* element );

};

#endif