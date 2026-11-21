################################################################################
#
# appstream
#
################################################################################

APPSTREAM_VERSION = v1.0.6
APPSTREAM_SITE = https://github.com/ximion/appstream.git
APPSTREAM_SITE_METHOD = git
APPSTREAM_LICENSE = LGPL-2.1+
APPSTREAM_LICENSE_FILES = COPYING
APPSTREAM_INSTALL_STAGING = YES
APPSTREAM_DEPENDENCIES = \
	host-gperf \
	host-libglib2 \
	host-pkgconf \
	libglib2 \
	libcurl \
	libxml2 \
	libyaml \
	libxmlb

# Keep the library + appstreamcli only; everything optional is off.
APPSTREAM_CONF_OPTS = \
	-Dstemming=false \
	-Dsystemd=false \
	-Dvapi=false \
	-Dqt=false \
	-Dcompose=false \
	-Dapt-support=false \
	-Dgir=false \
	-Dsvg-support=false \
	-Dzstd-support=false \
	-Ddocs=false \
	-Dapidocs=false \
	-Dinstall-docs=false

$(eval $(meson-package))
