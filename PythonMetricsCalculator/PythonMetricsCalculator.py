import os, imp, glob, sys
import urllib, zipfile
import unittest
import logging
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *


#
# PythonMetricsCalculator
#

class PythonMetricsCalculator( ScriptedLoadableModule ):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def __init__( self, parent ):
    ScriptedLoadableModule.__init__( self, parent )
    self.parent.title = "Python Metrics Calculator"
    self.parent.categories = [ "Perk Tutor" ]
    self.parent.dependencies = [ "PerkEvaluator" ]
    self.parent.contributors = [ "Matthew S. Holden (PerkLab, Queen's University), Tamas Ungi (PerkLab, Queen's University)" ]
    self.parent.helpText = """
    The Python Metric Calculator module is a hidden module for calculating metrics from sequences of transforms. For help on how to use this module visit: <a href='http://www.github.com/PerkTutor/PythonMetricsCalculator/wiki'>Python Metric Calculator</a>.
    """
    self.parent.acknowledgementText = """
    This work was was funded by Cancer Care Ontario and the Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO).
    """
    self.parent.hidden = True # Set to True when deploying

#
# PythonMetricsCalculatorWidget
#

class PythonMetricsCalculatorWidget( ScriptedLoadableModuleWidget ):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup( self ):
    ScriptedLoadableModuleWidget.setup( self )

  def cleanup( self ):
    pass

	
#
# PythonMetricsCalculatorLogic
#

class PythonMetricsCalculatorLogic( ScriptedLoadableModuleLogic ):
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget.
  Uses ScriptedLoadableModuleLogic base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  # We propose two concepts for metric distribution:
  # Sharing: Whether or not to sync the metric with every Perk Evaluator node
  # Ubiquity: Whether or not the metric spreads to every transform
  
  NEEDLE_LENGTH = 300 # 30cm is approximate need length
  
  ADDITIONAL_METRICS_URL = "https://github.com/PerkTutor/PythonMetrics/archive/master.zip"
  METRICS_ZIP_FILE_NAME = "PythonMetrics.zip"
   
  def __init__( self ):    
    self.realTimeMetrics = dict()
    self.realTimeMetricsTable = None
    self.realTimeProxyNodeCollection = vtk.vtkCollection()
    
    
  @staticmethod
  def Initialize():
    # Static variables (common to all instances of the PythonMetricsCalculatorLogic)
    PythonMetricsCalculatorLogic.AllMetricModules = dict()
    
    PythonMetricsCalculatorLogic.SetMRMLScene( None )
    PythonMetricsCalculatorLogic.SetPerkEvaluatorLogic( None )
    
    PythonMetricsCalculatorLogic.AddCoreMetricsToScene()
      
      
  @staticmethod
  def AddCoreMetricsToScene():
    coreMetricScriptDirectory = os.path.join( os.path.dirname( __file__ ), "PythonMetrics" )
    PythonMetricsCalculatorLogic.AddMetricsFromDirectoryToScene( coreMetricScriptDirectory )

      
  @staticmethod
  def DownloadAdditionalMetrics():
    metricsDownloadDirectory = slicer.mrmlScene.GetCacheManager().GetRemoteCacheDirectory()
    metricsFullZipFileName = os.path.join( metricsDownloadDirectory, PythonMetricsCalculatorLogic.METRICS_ZIP_FILE_NAME )

    # Download the zip file
    urllib.urlretrieve( PythonMetricsCalculatorLogic.ADDITIONAL_METRICS_URL, metricsFullZipFileName )

    # Extract the zip file
    metricsZipFile = zipfile.ZipFile( metricsFullZipFileName )
    metricsZipFile.extractall( metricsDownloadDirectory )
    
    additionalMetricScriptDirectory = os.path.join( metricsDownloadDirectory, "PythonMetrics-master" )
    PythonMetricsCalculatorLogic.AddMetricsFromDirectoryToScene( additionalMetricScriptDirectory )

    
  @staticmethod
  def AddMetricsFromDirectoryToScene( metricsDirectory ):
    metricScriptFiles = glob.glob( os.path.join( metricsDirectory, "[a-z]*.py" ) )
    for script in metricScriptFiles:
      slicer.util.loadNodeFromFile( script, "Python Metric Script" )
    
  
  @staticmethod 
  def SetMRMLScene( newScene ):
    PythonMetricsCalculatorLogic.mrmlScene = newScene
  
  
  @staticmethod
  def GetMRMLScene():
    if ( hasattr( PythonMetricsCalculatorLogic, "mrmlScene" )
      and PythonMetricsCalculatorLogic.mrmlScene != None ):
      return PythonMetricsCalculatorLogic.mrmlScene # Try to return the set scene
      
    try:
      return slicer.mrmlScene # Try to return Slicer's scene
    except:
      return None
  

  @staticmethod
  def SetPerkEvaluatorLogic( newPELogic ):
    PythonMetricsCalculatorLogic.peLogic = newPELogic    
    
  
  @staticmethod
  def GetPerkEvaluatorLogic():
    if ( hasattr( PythonMetricsCalculatorLogic, "peLogic" )
      and PythonMetricsCalculatorLogic.peLogic != None ):
      return PythonMetricsCalculatorLogic.peLogic # Try to return the set logic
      
    try:
      return slicer.modules.perkevaluator.logic() # Try to return the module's logic from Python
    except:
      return None
    
    
  @staticmethod
  def InitializeMetricsTable( metricsTable ):
    if ( metricsTable == None ):
      return
  
    metricsTable.GetTable().Initialize()
    
    # TODO: Make the more robust (e.g. qSlicerMetricsTableWidget::METRIC_TABLE_COLUMNS) 
    metricsTableColumnNames = [ "MetricName", "MetricRoles", "MetricUnit", "MetricValue" ]
    for columnName in metricsTableColumnNames:
      column = vtk.vtkStringArray()
      column.SetName( columnName )
      metricsTable.GetTable().AddColumn( column )
      
      
  @staticmethod   
  def OutputAllMetricsToMetricsTable( metricsTable, allMetrics ):
    if ( metricsTable == None ):
      return

    # Hold off on modified events until we are finished modifying
    modifyFlag = metricsTable.StartModify()
  
    PythonMetricsCalculatorLogic.InitializeMetricsTable( metricsTable )

    metricsTable.GetTable().SetNumberOfRows( len( allMetrics ) )
    insertRow = 0
    for metric in allMetrics.values():
      metricsTable.GetTable().SetValueByName( insertRow, "MetricName", metric.GetMetricName() )
      metricsTable.GetTable().SetValueByName( insertRow, "MetricRoles", metric.CombinedRoleString )
      metricsTable.GetTable().SetValueByName( insertRow, "MetricUnit", metric.GetMetricUnit() )
      metricsTable.GetTable().SetValueByName( insertRow, "MetricValue", metric.GetMetric() )
      insertRow += 1

    metricsTable.EndModify( modifyFlag )
    

  @staticmethod
  def RefreshMetricModules():
    PythonMetricsCalculatorLogic.AllMetricModules = PythonMetricsCalculatorLogic.GetFreshMetricModules()
    
  @staticmethod
  def GetFreshMetricModules():
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None ):
      return dict()
    
    # Setup the metrics currently associated with the selected PerkEvaluator node
    metricModuleDict = dict()
    
    # Grab all of the metric script nodes in the scene
    metricScriptNodes = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodesByClass( "vtkMRMLMetricScriptNode" )
    
    for i in range( metricScriptNodes.GetNumberOfItems() ):
      execDict = dict()
      currentMetricScriptNode = metricScriptNodes.GetItemAsObject( i )
      exec currentMetricScriptNode.GetPythonSourceCode() in execDict
      metricModuleDict[ currentMetricScriptNode.GetID() ] = execDict[ "PerkEvaluatorMetric" ]
    
    return metricModuleDict
    
  
  @staticmethod
  def GetFreshMetrics( peNodeID ):
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None ):
      return dict()
      
    peNode = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodeByID( peNodeID )
    if ( peNode == None ):
      return dict()
  
    # Get a fresh set of metric modules
    newMetricModules = PythonMetricsCalculatorLogic.GetFreshMetricModules()
    
    # Setup the metrics currently associated with the selected PerkEvaluator node
    metricDict = dict()
    
    # TODO: Make the reference role calling more robust (i.e. vtkMRMLPerkEvaluatorNode::METRIC_INSTANCE_REFERENCE_ROLE)
    for i in range( peNode.GetNumberOfNodeReferences( "MetricInstance" ) ):
      metricInstanceNode = peNode.GetNthNodeReference( "MetricInstance", i )
      if ( metricInstanceNode.GetAssociatedMetricScriptID() not in newMetricModules ):
        continue # Ignore metrics whose associated script is not loaded (e.g. if it has been deleted)
      
      associatedMetricModule = newMetricModules[ metricInstanceNode.GetAssociatedMetricScriptID() ]
      if ( PythonMetricsCalculatorLogic.AreMetricModuleRolesSatisfied( associatedMetricModule, metricInstanceNode ) ):
        metricDict[ metricInstanceNode.GetID() ] = associatedMetricModule() # Note: The brackets are important (they instantiate the instance)
        # Add the roles description (to make it easier to distinguish the same metric under different roles)
        metricDict[ metricInstanceNode.GetID() ].CombinedRoleString = metricInstanceNode.GetCombinedRoleString()
        
    # Add the anatomy to the fresh metrics
    PythonMetricsCalculatorLogic.AddAnatomyNodesToMetrics( metricDict )
    PythonMetricsCalculatorLogic.SetNeedleOrientation( metricDict, peNode )
   
    return metricDict
    
    
  @staticmethod
  def AreMetricModuleRolesSatisfied( metricModule, metricInstanceNode ):
    # Output whether or not the metric module has its roles completely satisfied by the metricInstance node
     
    rolesSatisfied = True
      
    for role in metricModule.GetRequiredAnatomyRoles():
      if ( metricInstanceNode.GetRoleID( role, metricInstanceNode.AnatomyRole ) == "" ):
        rolesSatisfied = False        
          
    for role in metricModule.GetAcceptedTransformRoles():
      if ( metricInstanceNode.GetRoleID( role, metricInstanceNode.TransformRole ) == "" ):
        rolesSatisfied = False
          
    return rolesSatisfied

    
  # Note: This modifies the inputted dictionary of metrics
  @staticmethod
  def AddAnatomyNodesToMetrics( metrics ): 
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None ):
      return
  
    # Keep track of which metrics all anatomies are sucessfully delivered to    
    unfulfilledAnatomies = []    
  
    for metricInstanceID in metrics:
      metricAnatomyRoles = metrics[ metricInstanceID ].GetRequiredAnatomyRoles()
      metricInstanceNode = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodeByID( metricInstanceID )
      
      for role in metricAnatomyRoles:
        anatomyNode = metricInstanceNode.GetRoleNode( role, metricInstanceNode.AnatomyRole )
        added = metrics[ metricInstanceID ].AddAnatomyRole( role, anatomyNode )
        
        if ( not added ):
          unfulfilledAnatomies.append( metricInstanceID )
          
    # In practice, the anatomies should always be fulfilled because we already filtered out those that could not be fulfilled
    # However, if the wrong type of node is selected, then this may return false
    for metricInstanceID in unfulfilledAnatomies:
      metrics.pop( metricInstanceID )

  
  @staticmethod
  def SetNeedleOrientation( metrics, peNode ):
    if( peNode == None ):
      return
      
    peNodeNeedleOrientation = [ 0, 0, 0 ]
    peNode.GetNeedleOrientation( peNodeNeedleOrientation )
    
    for metricInstanceID in metrics:
      metrics[ metricInstanceID ].NeedleOrientation = peNodeNeedleOrientation[:] # Element copy
      
        
  # Note: We are returning a list here, not a dictionary
  @staticmethod
  def GetAllRoles( metricScriptID, roleType ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return []
  
    if ( roleType == slicer.vtkMRMLMetricInstanceNode.TransformRole ):
      return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetAcceptedTransformRoles()
    elif ( roleType == slicer.vtkMRMLMetricInstanceNode.AnatomyRole ):
      return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetRequiredAnatomyRoles().keys()
    else:
      return []
    
    
  # Note: We are returning a string here
  @staticmethod
  def GetAnatomyRoleClassName( metricScriptID, role ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return "" 
      
    return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetRequiredAnatomyRoles()[ role ]
    
  # Note: We are returning a string here
  @staticmethod
  def GetMetricName( metricScriptID ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return ""
      
    return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetMetricName()
      
      
  # Note: We are returning a string here
  @staticmethod
  def GetMetricUnit( metricScriptID ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return ""
            
    return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetMetricUnit()      

   
  # Note: We are returning a bool here
  @staticmethod
  def GetMetricShared( metricScriptID ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return False
      
    try:
      return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetMetricShared()
    except: # TODO: Keep this for backwards compatibility with Python Metrics?
      return True
      
  
  # Note: We are returning a bool here
  @staticmethod
  def GetMetricPervasive( metricScriptID ):
    if ( metricScriptID not in PythonMetricsCalculatorLogic.AllMetricModules ):
      return False
    
    numTransformRoles = len( PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetAcceptedTransformRoles() ) #TODO: Add check for "Any" role?
    numAnatomyRoles = len( PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetRequiredAnatomyRoles().keys() )
    if ( numTransformRoles != 1 or numAnatomyRoles != 0 ):
      return False
      
    try:
      return PythonMetricsCalculatorLogic.AllMetricModules[ metricScriptID ].GetMetricPervasive()
    except: # TODO: Keep this for backwards compatibility with Python Metrics?
      return True
      
    
  @staticmethod
  def CalculateAllMetrics( peNodeID ):
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None or PythonMetricsCalculatorLogic.GetPerkEvaluatorLogic() == None ):
      return
      
    peNode = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodeByID( peNodeID )
    if ( peNode == None or peNode.GetTrackedSequenceBrowserNode() == None ):
      return dict()
      
    # Note that with the tracked sequence browser node, all of the frames should be synced.
    # So, we just need to iterate through the master sequence node
    masterSequenceNode = peNode.GetTrackedSequenceBrowserNode().GetMasterSequenceNode()
    if ( masterSequenceNode is None ):
      logging.warning( "Sequence browser has no associated sequence nodes." )
      return
    if ( masterSequenceNode.GetIndexType() != slicer.vtkMRMLSequenceNode.NumericIndex ):
      logging.warning( "Cannot analyze sequence with non-numeric index type." )
      return    
    if ( masterSequenceNode.GetNumberOfDataNodes() == 0 ):
      return
      
    proxyNodeCollection = vtk.vtkCollection()
    peNode.GetTrackedSequenceBrowserNode().GetAllProxyNodes( proxyNodeCollection )
  
    allMetrics = PythonMetricsCalculatorLogic.GetFreshMetrics( peNodeID )   

    # Start at the beginning (but remember where we were)
    originalItemNumber = peNode.GetTrackedSequenceBrowserNode().GetSelectedItemNumber()
    
    peNode.GetTrackedSequenceBrowserNode().SetSelectedItemNumber( 0 )
    peNode.GetTrackedSequenceBrowserNode().Modified() # Force update the proxy nodes
    peNode.SetAnalysisState( 0 )
  
    for i in range( masterSequenceNode.GetNumberOfDataNodes() ):
    
      try:
        time = float( masterSequenceNode.GetNthIndexValue( i ) )
      except:
        logging.warning( "Index:" + i + "has non-numeric index type." )
        continue
        
      if ( time < peNode.GetMarkBegin() or time > peNode.GetMarkEnd() ):
        continue
        
      # Update the scene so that all proxy nodes are at the appropriate frame
      peNode.GetTrackedSequenceBrowserNode().SetSelectedItemNumber( i )
      PythonMetricsCalculatorLogic.UpdateProxyNodeMetrics( allMetrics, proxyNodeCollection, time, None )
      
      # Update the progress
      progressPercent = 100 * ( time - peNode.GetMarkBegin() ) / ( peNode.GetMarkEnd() - peNode.GetMarkBegin() )
      peNode.SetAnalysisState( int( progressPercent ) )
      
      if ( peNode.GetAnalysisState() < 0 ): # If the user hits cancel
        break

    
    if ( peNode.GetAnalysisState() >= 0 ): # If the user has not hit cancel
      PythonMetricsCalculatorLogic.OutputAllMetricsToMetricsTable( peNode.GetMetricsTableNode(), allMetrics )
      
    peNode.GetTrackedSequenceBrowserNode().SetSelectedItemNumber( originalItemNumber ) # Scene automatically updated
    peNode.SetAnalysisState( 0 )

  
  @staticmethod  
  def UpdateProxyNodeMetrics( allMetrics, proxyNodeCollection, time, metricsTable ):
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None or PythonMetricsCalculatorLogic.GetPerkEvaluatorLogic() == None ):
      return
    
    # Get all transforms in the scene
    transformCollection = vtk.vtkCollection()
    PythonMetricsCalculatorLogic.GetPerkEvaluatorLogic().GetSceneVisibleTransformNodes( transformCollection )
    
    # Update all metrics associated with children of the recorded transform
    for i in range( proxyNodeCollection.GetNumberOfItems() ):
      currentProxyNode = proxyNodeCollection.GetItemAsObject( i )
      for j in range( transformCollection.GetNumberOfItems() ):
        currentTransformNode = transformCollection.GetItemAsObject( j )
        if ( PythonMetricsCalculatorLogic.GetPerkEvaluatorLogic().IsSelfOrDescendentNode( currentProxyNode, currentTransformNode ) ):
          PythonMetricsCalculatorLogic.UpdateMetrics( allMetrics, currentTransformNode, time, metricsTable )

  
  @staticmethod  
  def UpdateMetrics( allMetrics, transformNode, time, metricsTable ):
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None ):
      return
      
    # The assumption is that the scene is already appropriately updated
    matrix = vtk.vtkMatrix4x4()
    matrix.Identity()
    transformNode.GetMatrixTransformToWorld( matrix )
    point = [ matrix.GetElement( 0, 3 ), matrix.GetElement( 1, 3 ), matrix.GetElement( 2, 3 ), matrix.GetElement( 3, 3 ) ]
    
    for metricInstanceID in allMetrics:
      metric = allMetrics[ metricInstanceID ]
      metricInstanceNode = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodeByID( metricInstanceID )
      
      for role in metric.GetAcceptedTransformRoles():
        if ( metricInstanceNode.GetRoleID( role, metricInstanceNode.TransformRole ) == transformNode.GetID() ):
          try:
            metric.AddTimestamp( time, matrix, point, role )
          except TypeError: # Only look if there is an issue with the number of arguments
            metric.AddTimestamp( time, matrix, point ) # TODO: Keep this for backwards compatibility with Python Metrics?
      
    # Output the results to the metrics table node
    # TODO: Do we have to clear it all and re-write it all?
    if ( metricsTable != None ):
      PythonMetricsCalculatorLogic.OutputAllMetricsToMetricsTable( metricsTable, allMetrics )
      
      
  # Instance methods for real-time metric computation
  def SetupRealTimeMetricComputation( self, peNodeID ):
    if ( PythonMetricsCalculatorLogic.GetMRMLScene() == None  ):
      return
      
    peNode = PythonMetricsCalculatorLogic.GetMRMLScene().GetNodeByID( peNodeID )
    if ( peNode == None or peNode.GetMetricsTableNode() == None or peNode.GetTrackedSequenceBrowserNode() == None ):
      return
      
    self.realTimeMetrics = PythonMetricsCalculatorLogic.GetFreshMetrics( peNodeID )
    self.realTimeMetricsTable = peNode.GetMetricsTableNode()
    peNode.GetTrackedSequenceBrowserNode().GetAllProxyNodes( self.realTimeProxyNodeCollection )
    
    
  def UpdateRealTimeMetrics( self, time ):
    PythonMetricsCalculatorLogic.UpdateProxyNodeMetrics( self.realTimeMetrics, self.realTimeProxyNodeCollection, time, self.realTimeMetricsTable )

	
# PythonMetricsCalculatorTest

class PythonMetricsCalculatorTest( ScriptedLoadableModuleTest ):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp( self ):
    slicer.mrmlScene.Clear( 0 )

  def runTest( self ):
    """ Run as few or as many tests as needed here.
    """
    self.setUp()
    
    try:
      self.test_PythonMetricsCalculatorLumbar()
    except Exception, e:
      self.delayDisplay( "Lumbar test caused exception!\n" + str(e) )
    
    try:
      self.test_PythonMetricsCalculatorInPlane()
    except Exception, e:
      self.delayDisplay( "In-plane test caused exception!\n" + str(e) )
      
      
  def compareMetricsTables( self, trueMetricsTableNode, testMetricsTableNode ):
    # Check both tables to make sure they have the same number of rows    
    if ( trueMetricsTableNode.GetTable().GetNumberOfRows() != testMetricsTableNode.GetTable().GetNumberOfRows() ):
      print "True number of metrics:", trueMetricsTableNode.GetTable().GetNumberOfRows(), ", calculated number of metrics:", testMetricsTableNode.GetTable().GetNumberOfRows()
      raise Exception( "A different number of metrics was computed."  )

    # Compare the metrics to the expected results
    metricsMatch = True
    for i in range( testMetricsTableNode.GetTable().GetNumberOfRows() ):
      
      rowMatch = False # Need to match one row
      for j in range( trueMetricsTableNode.GetTable().GetNumberOfRows() ):
        
        colMatch = True # For a given row, need to match every column
        for k in range( trueMetricsTableNode.GetTable().GetNumberOfColumns() ):
          columnName = trueMetricsTableNode.GetTable().GetColumnName( k )
          trueValue = trueMetricsTableNode.GetTable().GetValueByName( j, columnName )
          testValue = testMetricsTableNode.GetTable().GetValueByName( i, columnName )
          if ( not testValue.IsValid() ):
            raise Exception( "The metrics table was improperly formatted." )
          if ( trueValue != testValue ):
            colMatch = False
        
        if ( colMatch ):
          rowMatch = True
          
      # If we could not find a row in the true table that matches the row in the test table, report an incorrect metric
      if ( not rowMatch ):
        print "Incorrect metric.",
        for k in range( testMetricsTableNode.GetTable().GetNumberOfColumns() ):
          print testMetricsTableNode.GetTable().GetColumnName( k ), testMetricsTableNode.GetTable().GetValue( i, k ),
        print ""          
        metricsMatch = False
        
    return metricsMatch
  

  def test_PythonMetricsCalculatorLumbar( self ):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """
    print( "CTEST_FULL_OUTPUT" )
    
    # These are the IDs of the relevant nodes
    tissueModelID = "vtkMRMLModelNode4"
    stylusTransformID = "vtkMRMLLinearTransformNode5"
    trueTableID = "vtkMRMLTableNode1"
    
    # Load the scene
    sceneFile = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), "Data", "Lumbar", "Scene_Lumbar.mrml" )
    activeScene = slicer.mrmlScene
    activeScene.Clear( 0 )
    activeScene.SetURL( sceneFile )
    if ( activeScene.Import() != 1 ):
      raise Exception( "Scene import failed. Scene file: " + sceneFile )

      
    # Manually load the sequence browser node from the transform buffer xml file
    transformBufferFile = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), "Data", "Lumbar", "TransformBuffer_Lumbar_Anonymous.xml" )
    success, trackedSequenceBrowserNode = slicer.util.loadNodeFromFile( transformBufferFile, "Tracked Sequence Browser", {}, True ) # This will load into activeScene, since activeScene == slicer.mrmlScene
    if ( not success or trackedSequenceBrowserNode is None ):
      raise Exception( "Could not load tracked sequence browser from: " + transformBufferFile )
      
    # Grab the relevant nodes from the scene
    tissueModelNode = activeScene.GetNodeByID( tissueModelID )
    if ( tissueModelNode is None ):
      raise Exception( "Bad tissue model." )
      
    stylusTransformNode = activeScene.GetNodeByID( stylusTransformID )
    if ( stylusTransformNode is None ):
      raise Exception( "Bad stylus transform." )
      
    trueTableNode = activeScene.GetNodeByID( trueTableID )
    if ( trueTableNode is None ):
      raise Exception( "Bad true metrics table." )
    
    # Setup the analysis
    peLogic = slicer.modules.perkevaluator.logic()
    PythonMetricsCalculatorLogic.Initialize()

    # Setup the parameters
    perkEvaluatorNode = activeScene.CreateNodeByClass( "vtkMRMLPerkEvaluatorNode" )
    perkEvaluatorNode.SetScene( activeScene )
    activeScene.AddNode( perkEvaluatorNode )
    
    metricsTableNode = activeScene.CreateNodeByClass( "vtkMRMLTableNode" )
    metricsTableNode.SetScene( activeScene )
    activeScene.AddNode( metricsTableNode )
    
    perkEvaluatorNode.SetTrackedSequenceBrowserNodeID( trackedSequenceBrowserNode.GetID() )
    perkEvaluatorNode.SetMetricsTableID( metricsTableNode.GetID() )

    # Now propagate the roles
    peLogic.SetMetricInstancesRolesToID( perkEvaluatorNode, stylusTransformNode.GetID(), "Needle", slicer.vtkMRMLMetricInstanceNode.TransformRole )
    peLogic.SetMetricInstancesRolesToID( perkEvaluatorNode, tissueModelNode.GetID(), "Tissue", slicer.vtkMRMLMetricInstanceNode.AnatomyRole )

    # Set the analysis begin and end times
    perkEvaluatorNode.UpdateMeasurementRange()
    
    # Calculate the metrics
    PythonMetricsCalculatorLogic.CalculateAllMetrics( perkEvaluatorNode.GetID() )
    
    # Check whether the computed metrics match the expected metrics
    metricsMatch = self.compareMetricsTables( trueTableNode, metricsTableNode )
        
    if ( not metricsMatch ):
      self.delayDisplay( "Test failed! Calculated metrics were not consistent with results." )
    else:
      self.delayDisplay( "Test passed! Calculated metrics match results!" )
      
    print "Lumbar test completed."
    self.assertTrue( metricsMatch )

    
  def test_PythonMetricsCalculatorInPlane( self ):
    """ Ideally you should have several levels of tests.  At the lowest level
    tests should exercise the functionality of the logic with different inputs
    (both valid and invalid).  At higher levels your tests should emulate the
    way the user would interact with your code and confirm that it still works
    the way you intended.
    One of the most important features of the tests is that it should alert other
    developers when their changes will have an impact on the behavior of your
    module.  For example, if a developer removes a feature that you depend on,
    your test should break so they know that the feature is needed.
    """
    print( "CTEST_FULL_OUTPUT" )
    
    # These are the IDs of the relevant nodes
    trackedSequenceBrowserID = "vtkMRMLSequenceBrowserNode1"
    tissueModelID = "vtkMRMLModelNode4"
    needleTransformID = "vtkMRMLLinearTransformNode4"
    trueTableID = "vtkMRMLTableNode1"
    
    
    # Load the scene
    sceneFile = os.path.join( os.path.dirname( os.path.abspath( __file__ ) ), "Data", "InPlane", "Scene_InPlane.mrml" )
    activeScene = slicer.mrmlScene
    activeScene.Clear( 0 )
    activeScene.SetURL( sceneFile )
    if ( activeScene.Import() != 1 ):
      raise Exception( "Scene import failed. Scene file: " + sceneFile )
      
    # Grab the relevant nodes from the scene
    trackedSequenceBrowserNode = activeScene.GetNodeByID( trackedSequenceBrowserID )
    if ( trackedSequenceBrowserNode is None ):
      raise Exception( "Bad sequence browser." )
      
    tissueModelNode = activeScene.GetNodeByID( tissueModelID )
    if ( tissueModelNode is None ):
      raise Exception( "Bad tissue model." )
      
    needleTransformNode = activeScene.GetNodeByID( needleTransformID )
    if ( needleTransformNode is None ):
      raise Exception( "Bad needle transform." )
      
    trueTableNode = activeScene.GetNodeByID( trueTableID )
    if ( trueTableNode is None ):
      raise Exception( "Bad true metrics table." )
    
    # Setup the analysis
    peLogic = slicer.modules.perkevaluator.logic()
    PythonMetricsCalculatorLogic.Initialize()

    # Setup the parameters
    perkEvaluatorNode = activeScene.CreateNodeByClass( "vtkMRMLPerkEvaluatorNode" )
    perkEvaluatorNode.SetScene( activeScene )
    activeScene.AddNode( perkEvaluatorNode )
    
    metricsTableNode = activeScene.CreateNodeByClass( "vtkMRMLTableNode" )
    metricsTableNode.SetScene( activeScene )
    activeScene.AddNode( metricsTableNode )
    
    perkEvaluatorNode.SetTrackedSequenceBrowserNodeID( trackedSequenceBrowserNode.GetID() )
    perkEvaluatorNode.SetMetricsTableID( metricsTableNode.GetID() )

    # Now propagate the roles
    peLogic.SetMetricInstancesRolesToID( perkEvaluatorNode, needleTransformNode.GetID(), "Needle", slicer.vtkMRMLMetricInstanceNode.TransformRole )
    peLogic.SetMetricInstancesRolesToID( perkEvaluatorNode, tissueModelNode.GetID(), "Tissue", slicer.vtkMRMLMetricInstanceNode.AnatomyRole )

    # Set the analysis begin and end times
    perkEvaluatorNode.UpdateMeasurementRange()
    
    # Calculate the metrics
    PythonMetricsCalculatorLogic.CalculateAllMetrics( perkEvaluatorNode.GetID() )
    
    # Check whether the computed metrics match the expected metrics
    metricsMatch = self.compareMetricsTables( trueTableNode, metricsTableNode )
        
    if ( not metricsMatch ):
      self.delayDisplay( "Test failed! Calculated metrics were not consistent with results." )
    else:
      self.delayDisplay( "Test passed! Calculated metrics match results!" )
      
    print "In-plane test completed."
    self.assertTrue( metricsMatch )