FROM atmoz/sftp:latest

# Set up SFTP user with password authentication
ENV SFTP_USERS="testuser:testpass:1000"

# Create the directory structure that matches US FL configuration
RUN mkdir -p /home/testuser/doc/cor /home/testuser/doc/Quarterly/Cor

# Copy mock data files
COPY mock_data/ /home/testuser/

# Set proper ownership (user will be created by SFTP_USERS env var)
RUN chown -R 1000:1000 /home/testuser/

# Expose SFTP port
EXPOSE 22
