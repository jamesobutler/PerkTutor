
#include "vtkWorkflowTask.h"

vtkStandardNewMacro( vtkWorkflowTask );


vtkWorkflowTask
::vtkWorkflowTask()
{
  this->Name = "";
  this->Instruction = "";
  this->Next = "";
  this->Prerequisite = "";
  this->Recovery = "";
}


vtkWorkflowTask
::~vtkWorkflowTask()
{
}


std::string vtkWorkflowTask
::ToXMLString()
{
  std::stringstream xmlstring;

  xmlstring << "<Task";
  xmlstring << " Name=\"" << this->Name << "\"";
  xmlstring << " Instruction=\"" << this->Instruction << "\"";
  xmlstring << " Next=\"" << this->Next << "\"";
  xmlstring << " Prerequisite=\"" << this->Prerequisite << "\"";
  xmlstring << " Recovery=\"" << this->Recovery << "\"";
  xmlstring << " />" << std::endl;

  return xmlstring.str();
}


void vtkWorkflowTask
::FromXMLElement( vtkXMLDataElement* element )
{

  if ( strcmp( element->GetName(), "Task" ) != 0 )
  {
    return;  // If it's not a "log" or is the wrong tool jump to the next.
  }

  this->Name = std::string( element->GetAttribute( "Name" ) );
  this->Instruction = std::string( element->GetAttribute( "Instruction" ) );
  this->Next = std::string( element->GetAttribute( "Next" ) );
  this->Prerequisite = std::string( element->GetAttribute( "Prerequisite" ) );
  this->Recovery = std::string( element->GetAttribute( "Recovery" ) );

}