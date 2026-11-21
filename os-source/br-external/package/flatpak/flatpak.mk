################################################################################
#
# flatpak
#
################################################################################

FLATPAK_VERSION = 1.16.6
FLATPAK_SITE = https://github.com/flatpak/flatpak/releases/download/$(FLATPAK_VERSION)
FLATPAK_SOURCE = flatpak-$(FLATPAK_VERSION).tar.xz
FLATPAK_LICENSE = LGPL-2.1+
FLATPAK_LICENSE_FILES = COPYING
FLATPAK_INSTALL_STAGING = YES
FLATPAK_DEPENDENCIES = \
	host-bison \
	host-libglib2 \
	host-pkgconf \
	host-python3 \
	host-python-pyparsing \
	appstream \
	bubblewrap \
	gdk-pixbuf \
	json-glib \
	libarchive \
	libcap \
	libcurl \
	libfuse3 \
	libglib2 \
	libgpgme \
	libseccomp \
	libxml2 \
	ostree \
	systemd \
	xdg-dbus-proxy \
	zstd

# Use the system bwrap / dbus-proxy / fusermount3 that Buildroot builds,
# instead of the bundled copies or a host-side lookup.
FLATPAK_CONF_OPTS = \
	-Dhttp_backend=curl \
	-Dsystem_bubblewrap=/usr/bin/bwrap \
	-Dsystem_dbus_proxy=/usr/bin/xdg-dbus-proxy \
	-Dsystem_fusermount=/usr/bin/fusermount3 \
	-Dsystem_helper=disabled \
	-Dsystemd=enabled \
	-Dlibzstd=enabled \
	-Dseccomp=enabled \
	-Ddconf=disabled \
	-Dmalcontent=disabled \
	-Dxauth=disabled \
	-Dselinux_module=disabled \
	-Dwayland_security_context=disabled \
	-Dgir=disabled \
	-Dgtkdoc=disabled \
	-Ddocbook_docs=disabled \
	-Dman=disabled \
	-Dtests=false \
	-Dinstalled_tests=false

$(eval $(meson-package))
