# How to deploy Infinispan

# Install OLM
kubectl apply -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/v0.28.0/crds.yaml --server-side=true
kubectl apply -f https://github.com/operator-framework/operator-lifecycle-manager/releases/download/v0.28.0/olm.yaml

# Wait OLM ready
kubectl wait --for=condition=Available --timeout=300s deployment/olm-operator -n olm
kubectl wait --for=condition=Available --timeout=300s deployment/catalog-operator -n olm

# Install Infinispan Operator
kubectl create -f https://operatorhub.io/install/infinispan.yaml

# Apply infinispan
kubectl apply -f infinispan.yaml

---

## Recommended startup order with Keycloak 26

When using this external Infinispan cluster together with Keycloak 26 (for example the `clusterless` setup in this repository), a known bug in the ProtoStream schema can prevent the Infinispan Console from parsing Keycloak entries. The recommended order is:

1. **Deploy and start Infinispan** using the steps above and wait until all pods in the `infinispan` namespace are `READY`.
2. **Start Keycloak** (for example with `docker compose up` or your preferred deployment method) so that it uploads `KeycloakModelSchema.proto` into the `___protobuf_metadata` cache.
3. **Apply the BitSet workaround** in the section below to fix the schema for the Console UI.

This order ensures that the schema is present in Infinispan and can then be adjusted so the Console is able to display Keycloak cache entries.

---

## Verifying Keycloak Infinispan integration

When using Keycloak 26 with the `clusterless` feature and an external Infinispan 15 cluster, the Infinispan Console might not be able to display entries for Keycloak caches (for example `sessions`, `clientSessions`) even though data is actually stored there.

To verify that Keycloak is using the external cluster, use the REST API exposed by Infinispan:

1. Port-forward the Hot Rod/REST service:

   ```bash
   kubectl port-forward svc/infinispan-cluster 11222:11222 -n infinispan
   ```

2. List caches:

   ```bash
   curl -u keycloak:KeycloakPass123 \
     "http://localhost:11222/rest/v2/caches"
   ```

3. Check cache sizes (example for `sessions` and `clientSessions`):

   ```bash
   curl -u keycloak:KeycloakPass123 \
     "http://localhost:11222/rest/v2/caches/sessions?action=size"

   curl -u keycloak:KeycloakPass123 \
     "http://localhost:11222/rest/v2/caches/clientSessions?action=size"
   ```

If the numbers increase after logging into Keycloak (for example by requesting a token), the external Infinispan cluster is working correctly even if the Console UI does not show individual entries.

### UI schema warning for Keycloak 26

With Keycloak 26, a ProtoStream schema named `KeycloakModelSchema.proto` is uploaded to the `___protobuf_metadata` cache. If the `BitSet` type is not known to Infinispan, the Console may display a warning similar to:

- `Schema KeycloakModelSchema.proto has errors`
- `Failed to resolve type of field "keycloak.InitializerState.segments"`
- `Type not found : org.infinispan.protostream.commons.BitSet`

This warning comes from the Console schema validator only and does **not** affect Keycloak functionality. Cache data is still stored and read correctly using REST API. However, without a small schema adjustment the Console cannot properly parse some Keycloak entries and might not show them in the UI.

### BitSet workaround for Console (remove field from InitializerState)

Upstream tracks this as a bug in the generated schema. As a workaround, you can remove the `BitSet` field from the `InitializerState` message in `KeycloakModelSchema.proto` so that the Infinispan Console can parse the schema:

1. Open the Infinispan Console.
2. Go to **Data container → Schemas**.
3. Open the `KeycloakModelSchema.proto` schema that Keycloak uploaded.
4. Scroll to the `InitializerState` message, which should look like this:

   ```proto
   message InitializerState {
     /**
      * @Basic
      */
     string realmId = 1;

     int32 segmentsCount = 2;

     org.infinispan.protostream.commons.BitSet segments = 3;
   }
   ```

5. Delete only the following line:

   ```proto
   org.infinispan.protostream.commons.BitSet segments = 3;
   ```

6. Save/update the schema in the Console.

After applying this workaround, the Console should stop flagging `KeycloakModelSchema.proto` as invalid and will be able to display Keycloak cache entries in the UI. This change is a UI-focused workaround for the BitSet bug; Keycloak itself continues to function correctly.