# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from app.controllers.main_handler import Index, Logout
from app.controllers.warehouse_handler import WarehouseData
from app.controllers.api import Location, LocationChildren, DistributionPoints, SubcountyLocations
from app.controllers.api import FormSerials, SerialsEndpoint, WarehouseBranches, DistributionPointsEndpoint
from app.controllers.api import WarehouseRecord, DistributionRecord, VhtCode, DeliverNets, ReceiveNets
from app.controllers.api import DistributeVillageNets, ReportersEndpoint, ReceiveVillageNets
from app.controllers.api import DistributeHouseholdNets
from app.controllers.api2 import LocationsEndpoint, LocationsCSVEndpoint, ReportersXLEndpoint
from app.controllers.api2 import DispatchSMS, DispatchSummary, Remarks, DistrictDispatchSummary
from app.controllers.api2 import DistrictStats, KannelSeries, ChartData
from app.controllers.reporters_handler import Reporters
from app.controllers.users_handler import Users
from app.controllers.groups_handler import Groups
from app.controllers.dispatch_handler import Dispatch
from app.controllers.dashboard_handler import Dashboard
from app.controllers.auditlog_handler import AuditLog
from app.controllers.smslog_handler import SMSLog
from app.controllers.settings_handler import Settings
from app.controllers.distributionpoints_handler import DistPoints
from app.controllers.coverage_handler import Coverage
from app.controllers.coveragemap_handler import CoverageMap
from app.controllers.charts_handler import Charts
from app.controllers.forgotpass_handler import ForgotPass
from app.controllers.hotline_handler import Hotline
from app.controllers.downloads_handler import Downloads
from app.controllers.adminunits_handler import AdminUnits
from app.controllers.subcounty_handler import SubCounty
from app.controllers.parish_handler import Parish
from app.controllers.stores_handler import Stores

URLS = (
    r'^/', Index,
    r'^/dashboard', Dashboard,
    r'/warehousedata', WarehouseData,
    r'/dispatch', Dispatch,
    r'/distributionpoints', DistPoints,
    r'/smslog', SMSLog,
    r'/adminunits', AdminUnits,
    r'/subcounties', SubCounty,
    r'/parishes', Parish,
    r'/coverage', Coverage,
    r'/coveragemap', CoverageMap,
    r'/charts', Charts,
    r'/hotline', Hotline,
    r'/downloads', Downloads,
    r'/stores', Stores,
    r'/reporters', Reporters,
    r'/auditlog', AuditLog,
    r'/settings', Settings,
    r'/users', Users,
    r'/groups', Groups,
    r'/logout', Logout,
    r'/forgotpass', ForgotPass,
    r'/kannelseries', KannelSeries,
    r'/chartdata', ChartData,
    # API stuff follows
    r'/api/v1/loc_children/(\d+)/?', LocationChildren,
    r'/api/v1/location/(\d+)/?', Location,
    r'/api/v1/distribution_points/(\d+)/?', DistributionPoints,
    r'/api/v1/subcountylocations/(\d+)/?', SubcountyLocations,
    r'/api/v1/warehousebranches/(\d+)/?', WarehouseBranches,
    r'/api/v1/warehouserecord/(\d+)/?', WarehouseRecord,
    r'/api/v1/dispatchrecord/(\d+)/?', DistributionRecord,
    r'/api/v1/formserials', FormSerials,
    r'/api/v1/forms_endpoint/(\w+)/?', SerialsEndpoint,
    r'/api/v1/dpoints_endpoint/(\w+)/?', DistributionPointsEndpoint,
    r'/api/v1/reporters_endpoint/(\w+)/?', ReportersEndpoint,
    r'/api/v1/locations_endpoint/(\w+)/?', LocationsEndpoint,
    r'/api/v1/locations_csvendpoint', LocationsCSVEndpoint,
    r'/api/v1/reporters_xlendpoint', ReportersXLEndpoint,
    r'/api/v1/vhtcode', VhtCode,
    r'/api/v1/deliver', DeliverNets,
    r'/api/v1/receive', ReceiveNets,
    r'/api/v1/got', ReceiveVillageNets,
    r'/api/v1/gave', DistributeHouseholdNets,
    r'/api/v1/distribute', DistributeVillageNets,
    r'/api/v1/remark', Remarks,
    r'/api/v1/dispatchsms/(\d+)/?', DispatchSMS,
    r'/api/v1/subcounty_disribution_summary', DispatchSummary,
    r'/api/v1/district_disribution_summary', DistrictDispatchSummary,
    r'/api/v1/districtstats', DistrictStats,
)
