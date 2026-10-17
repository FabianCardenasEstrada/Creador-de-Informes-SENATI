from sklearn.datasets import load_breast_cancer
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report

datos = load_breast_cancer()
X, y = datos.data, datos.target
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
esc = StandardScaler()
X_train = esc.fit_transform(X_train)
X_test = esc.transform(X_test)
modelo = LogisticRegression()
modelo.fit(X_train, y_train)
pred = modelo.predict(X_test)
print(accuracy_score(y_test, pred))
print(classification_report(y_test, pred))
