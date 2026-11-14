-- liquibase formatted sql

-- Service users authenticate with key pairs only (TYPE = SERVICE: no password).
-- Their public keys are attached when the service first runs outside a developer
-- machine (Airflow in Phase 4, CI/CD in Phase 7).

-- changeset streampulse:user-loader
create user if not exists svc_loader_${env}
    type = service
    default_role = loader_${env}
    default_warehouse = wh_load_${env}
    default_secondary_roles = ()
    comment = 'Raw file loader (${env})';
grant role loader_${env} to user svc_loader_${env};
-- rollback drop user if exists svc_loader_${env};

-- changeset streampulse:user-transformer
create user if not exists svc_transformer_${env}
    type = service
    default_role = transformer_${env}
    default_warehouse = wh_transform_${env}
    default_secondary_roles = ()
    comment = 'dbt (${env})';
grant role transformer_${env} to user svc_transformer_${env};
-- rollback drop user if exists svc_transformer_${env};

-- changeset streampulse:deployer-functional-roles context:dev
-- comment: Locally the DEV deployer user runs the loader and tests in each functional role.
grant role loader_${env} to user svc_deployer_${env};
grant role transformer_${env} to user svc_deployer_${env};
grant role reporter_${env} to user svc_deployer_${env};
grant role ai_readonly_${env} to user svc_deployer_${env};
grant role pii_reader_${env} to user svc_deployer_${env};
-- rollback revoke role pii_reader_${env} from user svc_deployer_${env};
-- rollback revoke role ai_readonly_${env} from user svc_deployer_${env};
-- rollback revoke role reporter_${env} from user svc_deployer_${env};
-- rollback revoke role transformer_${env} from user svc_deployer_${env};
-- rollback revoke role loader_${env} from user svc_deployer_${env};
