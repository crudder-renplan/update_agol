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
            datatype="GPStringHidden",
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
            displayName="Group(s) to share with",
            parameterType="Optional",
            datatype="GPString",
            category="AGOL Content",
            multiValue=True,
        )
        # set 3 of parameters - APRO Project
        pro_project = arcpy.Parameter(
            name="pro_project",
            displayName="ArcPRO Project",
            parameterType="Required",
            datatype="GPString",
            category="APRO Content",
        )
        map_name = arcpy.Parameter(
            name="map_name",
            displayName="Name of Map",
            parameterType="Required",
            datatype="GPString",
            category="APRO Content",
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
            pro_project,
            map_name,
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
            if parameters[0].value or parameters[1].value or parameters[2].value:
                user_list = []
                portal = GIS(
                    url=parameters[0], username=parameters[1], password=parameters[2]
                )
                portal_users = portal.users.search(
                    "!esri_ & !system_publisher", max_users=10000
                )
                for user in portal_users:
                    user_list.append(user.username)
                user_filter = parameters[3].filter
                user_filter.list = user_list
        # Dropdown for content associated with chosen user
        if (
            parameters[0].value
            or parameters[1].value
            or parameters[2].value
            or parameters[3].value
        ):
            content_list = []
            group_list = []
            for user in portal_users:
                if user.username == parameters[3]:
                    group_list = [str(group.title) for group in user.groups]
                    user_content = user.items()
                    for item in user_content:
                        if str(item.type) == "Feature Service":
                            content_list.append(str(item.title))
                    user_folders = user.folders
                    for folder in user_folders:
                        user_content = user.items(folder=folder["title"])
                        for item in user_content:
                            if str(item.type) == "Feature Service":
                                content_list.append(str(item.title))

            group_list.sort()
            group_filter = parameters[5].filter
            group_filter.list = group_list
            content_list.sort()
            content_filter = parameters[4].filter
            content_filter.list = content_list

        # dropdown for maps in apro project
        if parameters[5].altered:
            if parameters[5].value:
                prj = arcpy.mp.ArcGISProject(parameters[5])
                map_list = prj.listMaps()
                map_list.sort()
                map_filter = parameters[6].filter
                map_filter.list = map_filter
        return

    def updateMessages(self, parameters):
        """Modify the messages created by internal validation for each tool
        parameter.  This method is called after internal validation."""
        return

    def execute(self, parameters, messages):
        """The source code of the tool."""
        arcpy.env.overwriteOutput = True
        """ variables given"""
        portal_url = parameters[0]
        admin_user = parameters[1]
        admin_pass = parameters[2]
        content_owner = parameters[3]
        service_name = parameters[4]
        group_names = parameters[5]
        pro_project = parameters[6]
        map_name = parameters[7]
        share_to_org = parameters[8]
        share_to_everyone = parameters[9]

        """ main work """
        with tempfile.TemporaryDirectory() as LOCAL_PATH:
            draft_path = Path(LOCAL_PATH, f"{service_name}_WebUpdate.sddraft")
            SD_path = Path(LOCAL_PATH, f"{service_name}_WebUpdate.sd")
            #: Delete draft and definition if existing
            for file_path in (draft_path, SD_path):
                if file_path.exists():
                    arcpy.AddMessage(
                        f"deleting existing {str(file_path)}..."
                    )  # use str() wrapper around Path object so arcpy doesnt cry
                    file_path.unlink()

            arcpy.AddMessage("..Creating Service Definition from map layers...")
            stage_features(
                project=pro_project,
                prj_map=map_name,
                draft=draft_path,
                definition=SD_path,
            )

            arcpy.AddMessage(f"...Connecting to {portal_url}")
            gis = GIS(url=portal_url, username=admin_user, password=admin_pass)
            share_with_groups = [
                get_group_id(group_name=group, owner=content_owner, gis=gis)
                for group in group_names
            ]
            # check to see if the service exists and overwrite, otherwise publish new service
            try:
                arcpy.AddMessage("Looking for original service definition on portal...")
                service_def_item = gis.content.search(
                    query=f"title:{service_name} AND owner:{content_owner}",
                    item_type="Service Definition",
                )[0]
                arcpy.AddMessage(
                    f"\tFound SD: {service_def_item.title}, \n\tID: {service_def_item.id} \n\t\tUploading and overwriting…"
                )
                service_def_item.update(data=str(SD_path))
                arcpy.AddMessage("\tOverwriting existing feature service…")
                feature_service = service_def_item.publish(overwrite=True)
            except:
                arcpy.AddMessage("The service doesn't exist, creating new")
                arcpy.AddMessage("...uploading new content")
                source_item = gis.content.add(item_properties={}, data=str(SD_path))
                print("...publisihing new content")
                feature_service = source_item.publish()

            # share updated/new feature service
            if share_to_org or share_to_everyone or share_with_groups:
                arcpy.AddMessage(f"Setting sharing settings")
                feature_service.share(
                    org=share_to_org,
                    everyone=share_to_everyone,
                    groups=share_with_groups,
                )
        return


def stage_features(project, prj_map, draft, definition):
    arcpy.AddMessage("..Creating Service Definition from map layers...")
    prj = arcpy.mp.ArcGISProject(project)
    for m in prj.listMaps():
        if m.name == prj_map:
            arcpy.mp.CreateWebLayerSDDraft(
                map_or_layers=m,
                out_sddraft=draft,
                service_name=definition,
                server_type="HOSTING_SERVER",
                service_type="FEATURE_ACCESS",
                folder_name="",
                overwrite_existing_service=True,
                copy_data_to_server=True,
                enable_editing=True,
            )
            arcpy.StageService_server(
                in_service_definition_draft=draft,
                out_service_definition=definition,
            )


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
