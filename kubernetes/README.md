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