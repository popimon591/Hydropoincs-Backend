"""
URL configuration for hydro project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path,include
from importlib import import_module

from hydro.health import health_check



urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health_check, name="health-check"),
    path('api/v1/sensor/', include("hydro.api.v1.sensor.urls")),
    path("api/v1/user/", include("hydro.api.v1.user.urls")),
]

try:
    import_module("hydro.api.v1.device.urls")
except ModuleNotFoundError:
    pass
else:
    urlpatterns.append(path("api/v1/device/", include("hydro.api.v1.device.urls")))
