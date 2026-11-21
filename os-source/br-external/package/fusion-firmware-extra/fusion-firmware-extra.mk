################################################################################
#
# fusion-firmware-extra
#
################################################################################

# Same upstream tarball (and download dir) as Buildroot's linux-firmware.
FUSION_FIRMWARE_EXTRA_VERSION = $(LINUX_FIRMWARE_VERSION)
FUSION_FIRMWARE_EXTRA_SOURCE = $(LINUX_FIRMWARE_SOURCE)
FUSION_FIRMWARE_EXTRA_SITE = $(LINUX_FIRMWARE_SITE)
FUSION_FIRMWARE_EXTRA_DL_SUBDIR = linux-firmware
FUSION_FIRMWARE_EXTRA_LICENSE = Redistributable, see WHENCE
FUSION_FIRMWARE_EXTRA_LICENSE_FILES = WHENCE

# PC (PCIe/USB) parts only; the IPQ router chips are skipped.
FUSION_FIRMWARE_EXTRA_PATTERNS = \
	ath11k/QCA6390 ath11k/WCN6855 ath11k/QCA2066 \
	ath12k/WCN7850 \
	qca/hpbtfw* qca/hpnv* qca/htbtfw* qca/htnv* qca/hmtbtfw* qca/hmtnv*

define FUSION_FIRMWARE_EXTRA_INSTALL_TARGET_CMDS
	cd $(@D) && for p in $(FUSION_FIRMWARE_EXTRA_PATTERNS); do \
		for f in $$p; do \
			[ -e "$$f" ] || { echo "fusion-firmware-extra: $$p not in this release"; continue; }; \
			mkdir -p $(TARGET_DIR)/lib/firmware/$$(dirname $$f); \
			cp -a $$f $(TARGET_DIR)/lib/firmware/$$(dirname $$f)/; \
		done; \
	done
endef

$(eval $(generic-package))
