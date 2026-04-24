"use client";

import { useEffect, useMemo, useReducer, useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";

type TxnType = "income" | "expense";

type Transaction = {
  id: string;
  type: TxnType;
  category: string;
  amount: number;
  note: string;
  date: string;
};

const STORAGE_KEY = "tmc-next-finance-v1";

const categories: Record<TxnType, string[]> = {
  income: ["Salary", "Freelance", "Business", "Investments", "Other"],
  expense: ["Food", "Rent", "Transport", "Shopping", "Bills", "Entertainment", "Other"],
};

const initialForm = {
  type: "expense" as TxnType,
  category: "Food",
  amount: "",
  note: "",
  date: new Date().toISOString().slice(0, 10),
};

type PersistedState = {
  transactions: Transaction[];
  monthlyBudget: string;
  ready: boolean;
};

type PersistedAction =
  | { type: "hydrate"; payload: { transactions: Transaction[]; monthlyBudget: string } }
  | { type: "setTransactions"; payload: Transaction[] }
  | { type: "setMonthlyBudget"; payload: string };

const persistedInitialState: PersistedState = {
  transactions: [],
  monthlyBudget: "50000",
  ready: false,
};

function persistedReducer(state: PersistedState, action: PersistedAction): PersistedState {
  switch (action.type) {
    case "hydrate":
      return {
        transactions: action.payload.transactions,
        monthlyBudget: action.payload.monthlyBudget,
        ready: true,
      };
    case "setTransactions":
      return { ...state, transactions: action.payload };
    case "setMonthlyBudget":
      return { ...state, monthlyBudget: action.payload };
    default:
      return state;
  }
}

function inCurrentMonth(value: string) {
  const now = new Date();
  const d = new Date(value);
  return d.getMonth() === now.getMonth() && d.getFullYear() === now.getFullYear();
}

function formatINR(value: number) {
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 2,
  }).format(value);
}

export default function Home() {
  const [persisted, dispatch] = useReducer(persistedReducer, persistedInitialState);
  const [form, setForm] = useState(initialForm);
  const [error, setError] = useState("");

  const { transactions, monthlyBudget, ready } = persisted;

  useEffect(() => {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      try {
        const parsed = JSON.parse(raw) as {
          transactions?: Transaction[];
          monthlyBudget?: string;
        };
        dispatch({
          type: "hydrate",
          payload: {
            transactions: parsed.transactions ?? [],
            monthlyBudget: parsed.monthlyBudget ?? "50000",
          },
        });
      } catch {
        dispatch({
          type: "hydrate",
          payload: { transactions: [], monthlyBudget: "50000" },
        });
      }
    } else {
      dispatch({
        type: "hydrate",
        payload: { transactions: [], monthlyBudget: "50000" },
      });
    }
  }, []);

  useEffect(() => {
    if (!ready) return;
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ transactions, monthlyBudget }));
  }, [transactions, monthlyBudget, ready]);

  const monthlyTxns = useMemo(
    () => transactions.filter((txn) => inCurrentMonth(txn.date)),
    [transactions],
  );

  const stats = useMemo(() => {
    const income = monthlyTxns
      .filter((txn) => txn.type === "income")
      .reduce((sum, txn) => sum + txn.amount, 0);
    const expense = monthlyTxns
      .filter((txn) => txn.type === "expense")
      .reduce((sum, txn) => sum + txn.amount, 0);
    const balance = income - expense;
    const budget = Number(monthlyBudget || 0);
    const remaining = budget - expense;
    return { income, expense, balance, budget, remaining };
  }, [monthlyTxns, monthlyBudget]);

  function onTypeChange(next: TxnType) {
    setForm((prev) => ({
      ...prev,
      type: next,
      category: categories[next][0],
    }));
  }

  function onAddTransaction() {
    setError("");
    const amount = Number(form.amount);
    if (!Number.isFinite(amount) || amount <= 0) {
      setError("Amount must be greater than 0.");
      return;
    }

    const item: Transaction = {
      id: crypto.randomUUID(),
      type: form.type,
      category: form.category,
      amount,
      note: form.note.trim(),
      date: form.date,
    };

    dispatch({
      type: "setTransactions",
      payload: [...transactions, item].sort((a, b) => (a.date < b.date ? 1 : -1)),
    });
    setForm((prev) => ({ ...prev, amount: "", note: "" }));
  }

  function onDelete(id: string) {
    dispatch({
      type: "setTransactions",
      payload: transactions.filter((txn) => txn.id !== id),
    });
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-50 via-white to-emerald-50">
      <main className="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
        <header className="mb-8 flex flex-col gap-2">
          <p className="text-sm font-medium uppercase tracking-wide text-orange-600">Track My Cash</p>
          <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
            Personal Finance Tracker
          </h1>
          <p className="text-sm text-slate-600">
            Add income and expenses, monitor monthly cash flow, and keep your budget in control.
          </p>
        </header>

        <section className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-600">Income (This Month)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-emerald-600">
              {formatINR(stats.income)}
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-600">Expense (This Month)</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-rose-600">
              {formatINR(stats.expense)}
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-600">Net Balance</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-slate-900">
              {formatINR(stats.balance)}
            </CardContent>
          </Card>
          <Card className="border-0 shadow-sm">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm text-slate-600">Budget Remaining</CardTitle>
            </CardHeader>
            <CardContent className="text-2xl font-semibold text-indigo-600">
              {formatINR(stats.remaining)}
            </CardContent>
          </Card>
        </section>

        <section className="mt-6 grid gap-6 lg:grid-cols-3">
          <Card className="border-0 shadow-sm lg:col-span-1">
            <CardHeader>
              <CardTitle>Add Transaction</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="type">Type</Label>
                <Select value={form.type} onValueChange={(value) => onTypeChange(value as TxnType)}>
                  <SelectTrigger id="type">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="income">Income</SelectItem>
                    <SelectItem value="expense">Expense</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="category">Category</Label>
                <Select
                  value={form.category}
                  onValueChange={(value) =>
                    setForm((prev) => ({
                      ...prev,
                      category: value ?? categories[prev.type][0],
                    }))
                  }
                >
                  <SelectTrigger id="category">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {categories[form.type].map((item) => (
                      <SelectItem key={item} value={item}>
                        {item}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="amount">Amount</Label>
                <Input
                  id="amount"
                  type="number"
                  min="0"
                  step="0.01"
                  value={form.amount}
                  onChange={(e) => setForm((prev) => ({ ...prev, amount: e.target.value }))}
                  placeholder="0.00"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="date">Date</Label>
                <Input
                  id="date"
                  type="date"
                  value={form.date}
                  onChange={(e) => setForm((prev) => ({ ...prev, date: e.target.value }))}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="note">Note</Label>
                <Input
                  id="note"
                  value={form.note}
                  onChange={(e) => setForm((prev) => ({ ...prev, note: e.target.value }))}
                  placeholder="e.g. Grocery shopping"
                />
              </div>

              {error ? <p className="text-sm text-rose-600">{error}</p> : null}
              <Button className="w-full" onClick={onAddTransaction}>
                Add Entry
              </Button>

              <Separator />

              <div className="space-y-2">
                <Label htmlFor="budget">Monthly Budget</Label>
                <Input
                  id="budget"
                  type="number"
                  min="0"
                  value={monthlyBudget}
                  onChange={(e) =>
                    dispatch({ type: "setMonthlyBudget", payload: e.target.value })
                  }
                />
              </div>
            </CardContent>
          </Card>

          <Card className="border-0 shadow-sm lg:col-span-2">
            <CardHeader>
              <CardTitle>Transactions</CardTitle>
            </CardHeader>
            <CardContent>
              {!ready ? (
                <p className="text-sm text-slate-500">Loading your data...</p>
              ) : transactions.length === 0 ? (
                <p className="text-sm text-slate-500">
                  No transactions yet. Add your first income or expense entry.
                </p>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Date</TableHead>
                        <TableHead>Type</TableHead>
                        <TableHead>Category</TableHead>
                        <TableHead>Note</TableHead>
                        <TableHead className="text-right">Amount</TableHead>
                        <TableHead className="text-right">Action</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {transactions.map((txn) => (
                        <TableRow key={txn.id}>
                          <TableCell>{txn.date}</TableCell>
                          <TableCell>
                            <Badge
                              variant={txn.type === "income" ? "default" : "secondary"}
                              className={txn.type === "income" ? "bg-emerald-600 text-white" : "bg-rose-100 text-rose-700"}
                            >
                              {txn.type}
                            </Badge>
                          </TableCell>
                          <TableCell>{txn.category}</TableCell>
                          <TableCell>{txn.note || "-"}</TableCell>
                          <TableCell className="text-right font-medium">
                            {formatINR(txn.amount)}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button variant="ghost" size="sm" onClick={() => onDelete(txn.id)}>
                              Delete
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        </section>
      </main>
    </div>
  );
}
