# -*- coding: utf-8 -*-

"""URL definitions of the application. Regex based URLs are mapped to their
class handlers.
"""

from app.controllers.main_handler import Index, Logout
from app.controllers.warehouse_handler import WarehouseData
from app.controllers.api import Location, LocationChildren, DistributionPoints, SubcountyLocations
from app.controllers.api import FormSerials, SerialsEndpoint, WarehouseBranches
from app.controllers.api import WarehouseRecord, DistributionRecord
from app.controllers.reporters_handler import Reporters
from app.controllers.users_handler import Users
from app.controllers.groups_handler import Groups
from app.controllers.dispatch_handler import Dispatch
from app.controllers.dashboard_handler import Dashboard
from app.controllers.auditlog_handler import AuditLog
from app.controllers.settings_handler import Settings
from app.controllers.distributionpoints_handler import DistPoints

URLS = (
    r'^/', Index,
    r'^/dashboard', Dashboard,
    r'/warehousedata', WarehouseData,
    r'/dispatch', Dispatch,
    r'/distributionpoints', DistPoints,
    r'/api/v1/loc_children/(\d+)/?', LocationChildren,
    r'/api/v1/location/(\d+)/?', Location,
    r'/api/v1/distribution_points/(\d+)/?', DistributionPoints,
    r'/api/v1/subcountylocations/(\d+)/?', SubcountyLocations,
    r'/api/v1/warehousebranches/(\d+)/?', WarehouseBranches,
    r'/api/v1/warehouserecord/(\d+)/?', WarehouseRecord,
    r'/api/v1/dispatchrecord/(\d+)/?', DistributionRecord,
    r'/api/v1/formserials', FormSerials,
    r'/api/v1/forms_endpoint/(\w+)/?', SerialsEndpoint,
    r'/reporters', Reporters,
    r'/auditlog', AuditLog,
    r'/settings', Settings,
    r'/users', Users,
    r'/groups', Groups,
    r'/logout', Logout,
)
