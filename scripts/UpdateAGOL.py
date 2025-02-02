"""-------------------------------------------------------------------------------
 Tool Name:   UpdateAGOL
 Source Name: UpdateAGOL.py
 Author:      Charles Rudder
 Updated by:  Charles Rudder
 Description: Opens an Arcpro project and publishes/overwrites a hosted feature service
                based on the layers in the selected map then sets sharing.
-------------------------------------------------------------------------------"""
import arcpy
from arcgis.gis import GIS
import os

from datetime import datetime
import tempfile
from pathlib import Path


class UpdateAGOL(object):
    def __init__(self):
        """Define the tool (tool name is the name of the class)."""
        self.label = "Update Feature Service in AGOL"
        self.description = "Updates or creates a feature service in AGOL using an ArcPro \
                           project with map containing layers of interest"
        self.errorMessages = []
        self.canRunInBackground = False

    def getParameterInfo(self):
        """Define parameter definitions"""
        # set 1 of parameters - logs user into AGOL org to get other data
        portal_url = arcpy.Parameter(
            name="portal_url",
            displayName="AGOL URL",
            parameterType="Required",
            datatype="GPString",
            category="Login",
        )
        portal_url.value = "https://arcgis.com"

        admin_user = arcpy.Parameter(
            name="admin_user",
            displayName="Admin AGOL Username",
            parameterType="Required",
            datatype="GPString",
            category="Login",
        )
        admin_pass = arcpy.Parameter(
            name="admin_pass",
            displayName="Admin AGOL User Password",
            parameterType="Required",
            datatype="GPStringHidden",  # GPEncryptedString
            category="Login",
        )
        # set 2 of parameters - content settings
        content_owner = arcpy.Parameter(
            name="content_owner",
            displayName="Content Owner",
            parameterType="Required",
            datatype="GPString",
            category="AGOL Content",
        )
        service_name = arcpy.Parameter(
            name="service_name",
            displayName="Feature Service Name",
            parameterType="Required",
            datatype="GPString",
            category="AGOL Content",
        )
        group_names = arcpy.Parameter(
            name="groups",
            displayName="Group(s) to share with (Optional)",
            parameterType="Optional",
            datatype="GPString",
            category="AGOL Content",
            multiValue=True,
        )
        folder_name = arcpy.Parameter(
            name="folder_name",
            displayName="APRO Folder Name",
            parameterType="Optional",
            datatype="GPString",
            category="AGOL Content",
        )
        folder_name.value = ""

        # set 3 of parameters - APRO Project
        pro_project = arcpy.Parameter(
            name="pro_project",
            displayName="ArcPRO Project",
            parameterType="Required",
            datatype="DEFile",
            category="APRO Content",
        )
        map_name = arcpy.Parameter(
            name="map_name",
            displayName="Name of Map",
            parameterType="Required",
            datatype="GPString",
            category="APRO Content",
        )
        layers = arcpy.Parameter(
            name="layers",
            displayName="Layers to publish",
            parameterType="Optional",
            datatype="GPString",
            category="APRO Content",
            multiValue=True,
        )
        # set 4 of parameters - Sharing options
        shr_to_org = arcpy.Parameter(
            name="shr_to_org",
            displayName="Share with Organization?",
            parameterType="Required",
            datatype="GPBoolean",
            category="Sharing",
        )
        shr_to_org.value = "True"
        shr_to_everyone = arcpy.Parameter(
            name="shr_to_everyone",
            displayName="Share with Everyone?",
            parameterType="Required",
            datatype="GPBoolean",
            category="Sharing",
        )
        shr_to_everyone.value = "True"
        params = [
            portal_url,
            admin_user,
            admin_pass,
            content_owner,
            service_name,
            group_names,
            folder_name,
            pro_project,
            map_name,
            layers
            shr_to_org,
            shr_to_everyone,
        ]
        return params

    def isLicensed(self):
        """Set whether tool is licensed to execute."""
        return True

    def updateParameters(self, parameters):
        # Dropdown for users
        if parameters[0].altered or parameters[1].altered or parameters[2].altered:
            if parameters[0].value and parameters[1].value and parameters[2].value:
                user_list = []
                arcpy.AddMessage(parameters[0])
                portal = GIS(url=parameters[0].value, username=parameters[1].value, password=parameters[2].value, )
                portal_users = portal.users.search("!esri_ & !system_publisher", max_users=10000)
                for user in portal_users:
                    user_list.append(user.username)
                user_filter = parameters[3].filter
                user_filter.list = user_list
        # Dropdown for content associated with chosen user
        if (parameters[0].value and parameters[1].value and parameters[2].value and parameters[3].value):
            folder_list = []
            content_list = []
            group_list = []
            for user in portal_users:
                if user.username == parameters[3].value:
                    group_list = [str(group.title) for group in user.groups]
                    user_content = user.items()
                    for item in user_content:
                        if str(item.type) == "Feature Service":
                            content_list.append(str(item.title))
                    user_folders = user.folders
                    for folder in user_folders:
                        folder_name = folder["title"]
                        folder_list.append(folder_name)
                        user_content = user.items(folder=folder_name)
                        for item in user_content:
                            if str(item.type) == "Feature Service":
                                content_list.append(str(item.title))
            # load user folders
            folder_list.sort()
            folder_filter = parameters[4].filter
            folder_filter.list = folder_list
            # load user groups
            group_list.sort()
            group_filter = parameters[5].filter
            group_filter.list = group_list
            # load user content
            content_list.sort()
            content_filter = parameters[4].filter
            content_filter.list = content_list

        # dropdown for maps in apro project
        if parameters[7].altered:
            if parameters[7].value:
                prj = arcpy.mp.ArcGISProject(parameters[7].value)
                map_list = [str(mp.name) for mp in prj.listMaps()]
                # load map names
                map_list.sort()
                map_filter = parameters[8].filter
                map_filter.list = map_list

        if parameters[8].altered:
            if parameters[8].value:
                prj = arcpy.mp.ArcGISProject(parameters[7].value)
                mp = prj.listMaps(parameters[8].value)[0]
                lyr_list = [str(lyr.name) for lyr in mp.listLayers()]
                lyr_list.sort()
                lyr_filter = parameters[8].filter
                lyr_filter.list = lyr_list
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.env.overwriteOutput = True
        """ variables given"""
        # portal_url = parameters[0].valueAsText
        # admin_user = parameters[1].valueAsText
        # admin_pass = parameters[2].valueAsText
        # content_owner = parameters[3].valueAsText
        # service_name = parameters[4].valueAsText
        # group_names = parameters[5].valueAsText
        # pro_project = parameters[6].valueAsText
        # map_name = parameters[7].valueAsText
        # share_to_org = parameters[8].valueAsText
        # share_to_everyone = parameters[9].valueAsText

        portal_url = parameters[0]
        admin_user = parameters[1]
        admin_pass = parameters[2]
        content_owner = parameters[3]
        service_name = parameters[4]
        group_names = parameters[5]
        folder_name = parameters[6]
        pro_project = parameters[7]
        map_name = parameters[8]
        layers = parameters[9]
        share_to_org = parameters[10]
        share_to_everyone = parameters[11]
        if group_names == "":
            group_names = []
        else:
            group_names = group_names.split(";")

        """ date and time variable """
        now = datetime.now()
        time_string = datetime.strftime(now, '%Y-%d-%m_%I%M')

        """ set up pathing to service definitions """
        LOCAL_PATH = os.path.dirname(pro_project)
        SD_FOLDER = os.path.join(LOCAL_PATH, "ServiceDefinitions")
        if not os.path.exists(SD_FOLDER):
            os.mkdir(SD_FOLDER)

        """ main work """
        arcpy.AddMessage(f"...Connecting to {portal_url}")
        gis_conn = GIS(url=portal_url, username=admin_user, password=admin_pass)
        share_with_groups = [
            get_group_id(group_name=group, owner=content_owner, gis=gis_conn)
            for group in group_names
        ]
        # loop over layers selected and publish them or republish them
        prj = arcpy.mp.ArcGISProject(pro_project)
        mp = prj.listMaps(map_name)[0]
        for layer in layers:
            arcpy.AddMessage(layer.name)
            name = layer.name.replace(" ", "_")
            draft_path = os.path.join(SD_FOLDER, f"{name}_{time_string}_WebUpdate.sddraft")
            SD_path = os.path.join(SD_FOLDER, f"{name}_{time_string}_WebUpdate.sd")
            # toss any existing draft and sd files
            for f in [draft_path, SD_path]:
                if os.path.exists(f):
                    os.remove(f)
            arcpy.AddMessage("...Creating Service Definition from map layers...")
            sdd = mp.getWebLayerSharingDraft(server_type="HOSTING_SERVER",
                                             service_type="FEATURE",
                                             service_name=layer.name,
                                             layers_and_tables=layer)
            sdd.portalFolder = folder_name
            sdd.exportToSDDraft(out_sddraft=draft_path)

            # stage service
            arcpy.StageService_server(in_service_definition_draft=draft_path,
                                      out_service_definition=SD_path)
            # publish service
            feature_service = publish_service(service_name=layer.name, content_owner=content_owner,
                                              folder=folder_name, service_definition=SD_path)
            share_service(feature_service, share_to_org, share_to_everyone, share_with_groups)
        return


def stage_features(project, prj_map, service, draft, definition):
    prj = arcpy.mp.ArcGISProject(project)
    for m in prj.listMaps():
        if m.name == prj_map:
            arcpy.mp.CreateWebLayerSDDraft(map_or_layers=m, out_sddraft=draft, service_name=service,
                                           server_type="HOSTING_SERVER", service_type="FEATURE_ACCESS",
                                           folder_name="", overwrite_existing_service=True,
                                           copy_data_to_server=True, enable_editing=True, )
            arcpy.StageService_server(in_service_definition_draft=draft, out_service_definition=definition, )


def get_group_id(group_name, owner, gis):
    try:
        group = gis.groups.search(query=f"title: {group_name} AND owner: {owner}")
        return group[0].id
    except:
        return None


def get_wm_item_id(gis, wm_title, item_type="Web Map"):
    try:
        wm_search = gis.content.search(f"title: {wm_title}", item_type=item_type)
        for wm in wm_search:
            if wm.title == wm_title:
                return wm.id
    except AttributeError:
        print("no web map by that name exists, cannot find id to publish")


def publish_service(conn, service_name, content_owner, folder, service_definition):
    # check to see if the service exists and overwrite, otherwise publish new service
    try:
        print("...Looking for original service definition on portal...")
        service_def_item = conn.content.search(query=f"title:{service_name} AND owner:{content_owner}",
                                               item_type="Service Definition", )[0]
        print(
            f"... ...Found SD: {service_def_item.title}, \n\tID: {service_def_item.id} \n\t\tUploading and overwriting…"
        )
        service_def_item.update(data=str(service_definition))
        print(service_def_item)
        print("...Overwriting existing feature service…")
        feature_service = service_def_item.publish(overwrite=True)
    except:
        print("...The service doesn't exist, creating new")
        print("... ...uploading new content")
        source_item = conn.content.add(item_properties={}, data=str(service_definition), folder=folder)
        print("... ...publisihing new content")
        feature_service = source_item.publish()

    return feature_service


def share_service(feature_service, share_to_org, share_to_everyone, share_with_groups):
    # share updated/new feature service
    if share_to_org or share_to_everyone or share_with_groups:
        print(f"... Setting sharing settings")
        feature_service.share(org=share_to_org, everyone=share_to_everyone,
                              groups=share_with_groups, )


if __name__ == "__main__":
    arcpy.env.overwriteOutput = True
    # """ variables given"""
    # portal_url = parameters[0].valueAsText
    # admin_user = parameters[1].valueAsText
    # admin_pass = parameters[2].valueAsText
    # content_owner = parameters[3].valueAsText
    # service_name = parameters[4].valueAsText
    # group_names = parameters[5].valueAsText.split(";")
    # pro_project = parameters[6].valueAsText
    # map_name = parameters[7].valueAsText
    # share_to_org = parameters[8].valueAsText
    # share_to_everyone = parameters[9].valueAsText

    portal_url = "https://arcgis.com"
    admin_user = "Developer_CTW"
    admin_pass = "RenPlanD3v"
    content_owner = "Developer_CTW"
    service_name = "Change in Jobs_Housing Balance by Block_tileTest"
    group_names = ""
    pro_project = r"C:\OneDrive_RP\OneDrive - Renaissance Planning Group\SHARE\PMT\PMT.aprx"
    map_name = "Trend Tile Services"
    share_to_org = False
    share_to_everyone = False
    parameters = [portal_url, admin_user, admin_pass, content_owner, service_name,
                  group_names, pro_project, map_name, share_to_org, share_to_everyone]
    tool = UpdateAGOL()
    tool.execute(parameters=parameters, messages="")


