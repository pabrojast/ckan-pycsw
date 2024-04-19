FROM registry.access.redhat.com/ubi9/ubi:latest
LABEL maintainer="mjanez" \
      name="ckan-pycsw" \
      version="rhel-9"

# Set up environment variables
ENV PYCSW_PORT=8000
ENV CKAN_USER=ckan
ENV CKAN_GROUP=ckan
ENV CKAN_USER_SSH_PWD=ckan
ENV SSH_PORT=22
ENV APP_DIR=/app

# Install necessary packages and install Ansible
RUN dnf update -y && \
    # Basic packages
    dnf -y install sudo nano git wget gcc openssh-server openssl-devel libffi-devel make automake cmake \
    # Python dependencies
    python3 python3-pip libpq && \
    dnf clean all && \
    # Update pip
    pip3 install --upgrade pip && \
    # Install Ansible
    pip3 install --no-cache-dir virtualenv && \
    pip3 install --no-cache-dir ansible && \
    # Create ckan user/group with sudo access
    groupadd -g 92 ckan && \
    useradd -u 92 -m -d /home/ckan -s /bin/bash -g ckan ckan && \
    echo "ckan:${CKAN_USER_SSH_PWD}" | chpasswd && \
    echo "ckan ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/ckan && \
    chmod 0440 /etc/sudoers.d/ckan && \
    # Clean up
    dnf clean all

# SSH setup
RUN mkdir /var/run/sshd && \
    # Configure SSH for non-root public key authentication
    sed -i 's/#PermitRootLogin prohibit-password/PermitRootLogin yes/' /etc/ssh/sshd_config && \
    sed 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@g' -i /etc/pam.d/sshd && \
    # Generate host keys
    ssh-keygen -A

# Copy the public key
RUN if [ -f .ssh/keys/ssh.pub ]; then \
    cp .ssh/keys/ssh.pub /home/ckan/.ssh/authorized_keys && \
    chown ckan:ckan /home/ckan/.ssh/authorized_keys && \
    chmod 600 /home/ckan/.ssh/authorized_keys; \
fi

# Clone the git repository
RUN git clone https://github.com/mjanez/ckan-pycsw ${APP_DIR}

# Assign all of app_dir to the ckan user
RUN chown -R ${CKAN_USER}:${CKAN_GROUP} ${APP_DIR}

EXPOSE ${PYCSW_PORT} ${SSH_PORT} 

# Keep container running starts SSHD
CMD ["/usr/sbin/sshd", "-D"]
