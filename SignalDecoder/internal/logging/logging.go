package logging

import (
	"github.com/fatih/color"
)

// functions to change color of text.
var (
	ErrLog  = color.New(color.FgRed).Add(color.Bold).SprintFunc()
	StatLog = color.New(color.FgGreen).Add(color.Bold).SprintFunc()
)
